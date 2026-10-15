# UI component sources

Button, Card, Input, Label, Badge, Alert and Table are source-owned shadcn/ui
components downloaded from the official Tailwind 3 `new-york` registry:
`https://v3.shadcn.com/r/styles/new-york/<component>.json`.

See [manual setup](https://v3.shadcn.com/docs/installation/manual) and the upstream
[MIT license](https://github.com/shadcn-ui/ui/blob/main/LICENSE.md), included in
`LICENSE.txt` beside these files. There is no shadcn runtime package; the component
source belongs to the application.

Local adaptations: imports resolve to the feature's `cn` helper; Button and Input
use 44px targets; Input includes invalid-field styling. The feature adapters in
`../ui.tsx` compose these components with the existing agricultural theme,
semantic headings, status roles, evidence rendering and approval filtering.

`native-select.tsx` is a local native HTML adapter using the same Tailwind theme,
not shadcn's Radix Select. It preserves existing controlled values, empty options,
onChange events, mobile selection and keyboard behavior. Existing plan section
links remain route navigation rather than being mislabeled as in-page tabs.
