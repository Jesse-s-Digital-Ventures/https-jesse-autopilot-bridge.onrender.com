---
applyTo: "src/components/ui/**/*.tsx,src/components/shared/**/*.tsx"
---

- Prefer existing shadcn/ui components; check for an existing component before creating a new one.
- Style with Tailwind v4 using mobile-first classes; add responsive variants for larger screens.
- Use Lucide React icons (import from 'lucide-react'); avoid inline SVGs unless necessary.
- Ensure accessible interactions (keyboard focus, ARIA where applicable) and touch targets ≥44px.
- Avoid client components unless interactivity is required; keep pure presentational pieces server-rendered.
- Co-locate component tests in __tests__ where applicable; use Vitest.
