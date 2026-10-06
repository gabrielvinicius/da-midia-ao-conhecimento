import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Search } from "lucide-react";
import { semanticSearch } from "@/features/summarization/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

const MIN_QUERY_LENGTH = 3;

export const formatTimestamp = (seconds?: number | null): string | null => {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return null;
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
};

const SearchPage = () => {
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");

  const { data, isFetching, isError } = useQuery({
    queryKey: ["semantic-search", query],
    queryFn: () => semanticSearch(query),
    enabled: query.length >= MIN_QUERY_LENGTH,
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setQuery(input.trim());
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Busca</h1>
        <p className="text-muted-foreground">
          Pergunte em linguagem natural. A busca encontra trechos pelo significado, mesmo que as
          palavras exatas não tenham sido ditas.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex max-w-2xl gap-2" role="search">
        <Input
          aria-label="Pergunta"
          placeholder="Ex.: em qual aula expliquei a regra da cadeia?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <Button type="submit" disabled={input.trim().length < MIN_QUERY_LENGTH}>
          <Search className="mr-2 h-4 w-4" />
          Buscar
        </Button>
      </form>

      {isFetching && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Buscando...
        </div>
      )}

      {isError && <p className="text-sm text-red-600">Não foi possível realizar a busca.</p>}

      {!isFetching && data && data.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Nenhum trecho encontrado. Mídias processadas antes da indexação precisam ser reprocessadas.
        </p>
      )}

      <div className="grid gap-4">
        {data?.map((result, index) => {
          const start = formatTimestamp(result.start);
          const end = formatTimestamp(result.end);
          return (
            <Card key={`${result.media_id}-${index}`}>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center justify-between text-base">
                  {/* Com horário, a mídia abre no momento do trecho (?t=segundos). */}
                  <Link
                    to={`/media/${result.media_id}${result.start != null ? `?t=${Math.floor(result.start)}` : ""}`}
                    className="hover:underline"
                  >
                    {result.start != null ? "Abrir no trecho" : "Abrir mídia"}
                  </Link>
                  <Badge variant="secondary">{result.relevance.toFixed(0)}% de relevância</Badge>
                </CardTitle>
                {start && (
                  <CardDescription>
                    Trecho em {start}
                    {end ? ` – ${end}` : ""}
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed">{result.content}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
};

export default SearchPage;
