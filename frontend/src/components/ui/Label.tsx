import * as React from "react"
import * as LabelPrimitive from "@radix-ui/react-label"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "../../lib/utils"

// Bloco com a linha de 24px que o rótulo ocupava como elemento inline: no
// Tailwind 4, o space-y-* põe a margem no próprio rótulo, e margem vertical
// em elemento inline é ignorada (o campo colava no rótulo).
const labelVariants = cva(
  "block text-sm font-medium leading-6 peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
)

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> & 
  VariantProps<typeof labelVariants>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn(labelVariants(), className)}
    {...props}
  />
))
Label.displayName = LabelPrimitive.Root.displayName

export { Label }
