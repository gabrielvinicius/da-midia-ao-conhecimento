import { Input } from "@/components/ui/Input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";
import type { ProviderOption } from "../api";

export const AUTO_PROVIDER_VALUE = "__auto__";

type Props = {
  id: string;
  options: ProviderOption[];
  value: string | undefined;
  onChange: (value: string | undefined) => void;
  disabled?: boolean;
  /** Oferece "Automático" (o padrão do sistema), que envia nenhum valor. */
  allowAuto?: boolean;
  /** Sem a lista de /providers, um campo de texto permite digitar o nome. */
  fallbackPlaceholder: string;
};

export function ProviderSelect({ id, options, value, onChange, disabled, allowAuto, fallbackPlaceholder }: Props) {
  if (options.length === 0) {
    return (
      <Input
        id={id}
        placeholder={fallbackPlaceholder}
        disabled={disabled}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value.trim() || undefined)}
      />
    );
  }
  return (
    <Select
      value={value ?? (allowAuto ? AUTO_PROVIDER_VALUE : undefined)}
      onValueChange={(next) => onChange(next === AUTO_PROVIDER_VALUE ? undefined : next)}
      disabled={disabled}
    >
      <SelectTrigger id={id}>
        <SelectValue placeholder="Selecione" />
      </SelectTrigger>
      <SelectContent>
        {allowAuto && <SelectItem value={AUTO_PROVIDER_VALUE}>Automático</SelectItem>}
        {options.map((p) => (
          <SelectItem key={p.name} value={p.name}>
            <div className="flex flex-col gap-0.5">
              <span className="text-sm font-medium">{p.label || p.name}</span>
              {p.description && <span className="text-xs text-muted-foreground">{p.description}</span>}
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
