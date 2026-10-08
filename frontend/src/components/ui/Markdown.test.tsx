import { render, screen } from "@testing-library/react";
import { Markdown } from "./Markdown";

describe("Markdown", () => {
  it("formata títulos, listas, citações e destaques sem deixar marcações cruas", () => {
    const { container } = render(
      <Markdown
        text={[
          "# Título",
          "Texto com **negrito** e _itálico_.",
          "---",
          "> [00:00] Primeiro trecho.",
          ">",
          "> continua.",
          "- um",
          "- dois",
          "1. primeiro",
        ].join("\n")}
      />,
    );
    expect(screen.getByRole("heading", { name: "Título" })).toBeInTheDocument();
    expect(screen.getByText("negrito").tagName).toBe("STRONG");
    expect(screen.getByText("itálico").tagName).toBe("EM");
    expect(container.querySelector("hr")).not.toBeNull();
    expect(container.querySelectorAll("blockquote")).toHaveLength(1);
    expect(container.querySelector("blockquote")?.textContent).toBe("[00:00] Primeiro trecho. continua.");
    expect(container.querySelectorAll("ul li")).toHaveLength(2);
    expect(container.querySelectorAll("ol li")).toHaveLength(1);
    expect(container.textContent).not.toMatch(/\*\*|^---|>/);
  });
});
