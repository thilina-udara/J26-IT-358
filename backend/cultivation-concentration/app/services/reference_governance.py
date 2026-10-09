"""Persistent independent review governance, separate from model training."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException
from app.services.expert_reviews import digest

class ReferenceStore:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connection() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS reviewers(id TEXT PRIMARY KEY,payload TEXT NOT NULL,actor TEXT NOT NULL,recorded_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS rubrics(id TEXT PRIMARY KEY,payload TEXT NOT NULL,actor TEXT NOT NULL,recorded_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cases(id TEXT NOT NULL,version INTEGER NOT NULL,payload TEXT NOT NULL,digest TEXT NOT NULL,
              actor TEXT NOT NULL,recorded_at TEXT NOT NULL,PRIMARY KEY(id,version));
            CREATE TABLE IF NOT EXISTS assignments(case_id TEXT NOT NULL,version INTEGER NOT NULL,reviewer_id TEXT NOT NULL,
              rubric TEXT NOT NULL,actor TEXT NOT NULL,recorded_at TEXT NOT NULL,PRIMARY KEY(case_id,version,reviewer_id,rubric));
            CREATE TABLE IF NOT EXISTS reviews(case_id TEXT NOT NULL,version INTEGER NOT NULL,reviewer_id TEXT NOT NULL,
              rubric TEXT NOT NULL,payload TEXT NOT NULL,received_at TEXT NOT NULL,PRIMARY KEY(case_id,version,reviewer_id,rubric));
            CREATE TABLE IF NOT EXISTS adjudications(case_id TEXT NOT NULL,version INTEGER NOT NULL,rubric TEXT NOT NULL,
              reviewer_id TEXT NOT NULL,payload TEXT NOT NULL,recorded_at TEXT NOT NULL,PRIMARY KEY(case_id,version,rubric));
            ''')
            for table in ('reviewers','rubrics','cases','assignments','reviews','adjudications'):
                for operation in ('UPDATE','DELETE'):
                    db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'Immutable governance record'); END")

    @contextmanager
    def connection(self):
        db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()

    def now(self):return datetime.now(timezone.utc).isoformat()

    def require(self,db,table,identity):
        row=db.execute(f'SELECT payload FROM {table} WHERE id=?',(identity,)).fetchone()
        if row is None:raise HTTPException(404,'Governance record not found')
        return json.loads(row['payload'])

    def latest(self,db,case_id,version):
        row=db.execute('SELECT * FROM cases WHERE id=? ORDER BY version DESC LIMIT 1',(case_id,)).fetchone()
        if row is None:raise HTTPException(404,'Case not found')
        if row['version']!=version:raise HTTPException(409,'Case version superseded')
        return row,json.loads(row['payload'])

    def record(self,kind,value,actor):
        try:
            with self.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                if kind=='reviewers':identity=value.reviewer_id
                elif kind=='rubrics':
                    identity=value.rubric_version
                    if value.approved and not value.approval_evidence:raise HTTPException(422,'Documented rubric approval required')
                else:
                    previous=db.execute('SELECT MAX(version) FROM cases WHERE id=?',(value.case.case_id,)).fetchone()[0]
                    if value.case_version!=(previous or 0)+1:raise HTTPException(409,'Case versions must be sequential')
                    # Only evidence-backed real cases can enter the review queue.
                    if value.provenance!='verified_real' or not all((value.provenance_evidence,value.consent_evidence,
                        value.privacy_approval_evidence,value.season_mapping_evidence,value.case.scenario.season_verified)):
                        raise HTTPException(422,'Verified real provenance, consent, privacy and season evidence required')
                    if value.case.forecast_cutoff>datetime.now(timezone.utc):raise HTTPException(422,'Case cutoff cannot be future')
                    db.execute('INSERT INTO cases VALUES(?,?,?,?,?,?)',(value.case.case_id,value.case_version,
                        value.model_dump_json(),digest(value.case),actor,self.now()))
                    return {'status':'recorded','training_eligible':False}
                db.execute(f'INSERT INTO {kind} VALUES(?,?,?,?)',(identity,value.model_dump_json(),actor,self.now()))
            return {'status':'recorded','training_eligible':False}
        except sqlite3.IntegrityError as exc:raise HTTPException(409,'Immutable record already exists') from exc

    def assign(self,case_id,version,reviewer,rubric,actor):
        try:
            with self.connection() as db:
                db.execute('BEGIN IMMEDIATE');self.latest(db,case_id,version)
                if db.execute('SELECT 1 FROM adjudications WHERE case_id=? AND version=? AND rubric=?',(case_id,version,rubric)).fetchone():
                    raise HTTPException(409,'Adjudicated review round is closed')
                expert=self.require(db,'reviewers',reviewer);rule=self.require(db,'rubrics',rubric)
                if not expert['verified'] or not rule['approved']:raise HTTPException(409,'Verified reviewer and approved rubric required')
                if expert['can_adjudicate']:raise HTTPException(409,'Adjudicators cannot receive independent-review assignments')
                db.execute('INSERT INTO assignments VALUES(?,?,?,?,?,?)',(case_id,version,reviewer,rubric,actor,self.now()))
            return {'status':'assigned'}
        except sqlite3.IntegrityError as exc:raise HTTPException(409,'Assignment already exists') from exc

    def review(self,case_id,value,reviewer):
        try:
            with self.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                if db.execute('SELECT 1 FROM adjudications WHERE case_id=? AND version=? AND rubric=?',
                    (case_id,value.case_version,value.rubric_version)).fetchone():raise HTTPException(409,'Adjudicated review round is closed')
                assignment=db.execute('SELECT * FROM assignments WHERE case_id=? AND version=? AND reviewer_id=? AND rubric=?',
                    (case_id,value.case_version,reviewer,value.rubric_version)).fetchone()
                if assignment is None:raise HTTPException(403,'Review assignment required')
                expert=self.require(db,'reviewers',reviewer)
                if not expert['verified']:raise HTTPException(403,'Verified reviewer required')
                row,case=self.latest(db,case_id,value.case_version)
                if value.case_digest!=row['digest']:raise HTTPException(409,'Case digest mismatch')
                if value.reviewed_at.tzinfo is None or not datetime.fromisoformat(case['case']['forecast_cutoff'])<=value.reviewed_at<=datetime.now(timezone.utc):
                    raise HTTPException(422,'Invalid review chronology')
                if value.reviewed_at<datetime.fromisoformat(assignment['recorded_at']):raise HTTPException(422,'Review predates assignment')
                db.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?)',(case_id,value.case_version,reviewer,value.rubric_version,value.model_dump_json(),self.now()))
            return {'status':'review_recorded','training_eligible':False}
        except sqlite3.IntegrityError as exc:raise HTTPException(409,'Review is immutable; duplicate rejected') from exc

    def assigned_case(self,case_id,version,rubric,reviewer):
        with self.connection() as db:
            if db.execute('SELECT 1 FROM assignments WHERE case_id=? AND version=? AND rubric=? AND reviewer_id=?',
                (case_id,version,rubric,reviewer)).fetchone() is None:raise HTTPException(403,'Review assignment required')
            row,payload=self.latest(db,case_id,version)
            # Blind independent review: no peers, targets or private evidence metadata.
            return dict(case=payload['case'],case_version=version,case_digest=row['digest'],rubric=self.require(db,'rubrics',rubric)['rubric_text'])

    def status(self,case_id,version,rubric):
        with self.connection() as db:
            _,case=self.latest(db,case_id,version)
            rule=self.require(db,'rubrics',rubric)
            rows=db.execute('SELECT * FROM reviews WHERE case_id=? AND version=? AND rubric=?',(case_id,version,rubric)).fetchall()
            labels=[json.loads(r['payload'])['label'] for r in rows]
            pairs=len(labels)*(len(labels)-1)//2
            agrees=sum(labels[i]==labels[j] for i in range(len(labels)) for j in range(i+1,len(labels)))
            decision=db.execute('SELECT payload FROM adjudications WHERE case_id=? AND version=? AND rubric=?',(case_id,version,rubric)).fetchone()
            resolved=json.loads(decision['payload'])['decision'] if decision else None
            verified=all(self.require(db,'reviewers',r['reviewer_id'])['verified'] for r in rows)
            eligible=bool(len(rows)>=2 and verified and rule['approved'] and resolved in ('Low','Medium','High'))
            return dict(case_version=version,review_count=len(rows),label_counts={l:labels.count(l) for l in ('Low','Medium','High','Uncertain')},
                pair_count=pairs,agreement_count=agrees,pairwise_agreement=agrees/pairs if pairs else None,
                conflicting=len(set(labels))>1,adjudication=resolved,unresolved=resolved in (None,'unresolved','Uncertain'),
                training_eligible=eligible,eligibility_scope='label governance only; frozen split approval additionally required')

    def adjudicate(self,case_id,value,reviewer):
        try:
            with self.connection() as db:
                db.execute('BEGIN IMMEDIATE');self.latest(db,case_id,value.case_version)
                expert=self.require(db,'reviewers',reviewer)
                if not expert['verified'] or not expert['can_adjudicate']:raise HTTPException(403,'Verified adjudicator required')
                rows=db.execute('SELECT reviewer_id,payload FROM reviews WHERE case_id=? AND version=? AND rubric=?',(case_id,value.case_version,value.rubric_version)).fetchall()
                if len(rows)<2:raise HTTPException(409,'At least two independent reviews required')
                if reviewer in {r['reviewer_id'] for r in rows}:raise HTTPException(403,'Adjudicator must be independent of initial reviewers')
                if not self.require(db,'rubrics',value.rubric_version)['approved']:raise HTTPException(409,'Approved rubric required')
                labels=[json.loads(r['payload'])['label'] for r in rows]
                pairs=len(labels)*(len(labels)-1)//2
                agreement=sum(labels[i]==labels[j] for i in range(len(labels)) for j in range(i+1,len(labels)))
                payload=dict(value.model_dump(mode='json'),agreement_before_adjudication=dict(pair_count=pairs,
                    agreement_count=agreement,pairwise_agreement=agreement/pairs,label_counts={l:labels.count(l) for l in ('Low','Medium','High','Uncertain')}))
                db.execute('INSERT INTO adjudications VALUES(?,?,?,?,?,?)',(case_id,value.case_version,value.rubric_version,reviewer,json.dumps(payload),self.now()))
            return self.status(case_id,value.case_version,value.rubric_version)
        except sqlite3.IntegrityError as exc:raise HTTPException(409,'Adjudication immutable') from exc

    def adjudication_packet(self,case_id,version,rubric,reviewer):
        with self.connection() as db:
            expert=self.require(db,'reviewers',reviewer)
            if not expert['verified'] or not expert['can_adjudicate']:raise HTTPException(403,'Verified adjudicator required')
            _,case=self.latest(db,case_id,version)
            rows=db.execute('SELECT reviewer_id,payload FROM reviews WHERE case_id=? AND version=? AND rubric=?',
                (case_id,version,rubric)).fetchall()
            if len(rows)<2:raise HTTPException(409,'Two reviews required before adjudication')
            if reviewer in {r['reviewer_id'] for r in rows}:raise HTTPException(403,'Independent adjudicator required')
            return dict(case=case['case'],case_version=version,rubric=self.require(db,'rubrics',rubric)['rubric_text'],
                reviews=[dict(reviewer_id=r['reviewer_id'],review=json.loads(r['payload'])) for r in rows])
