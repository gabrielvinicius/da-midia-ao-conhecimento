import { fireEvent, render, screen } from "@testing-library/react";
import { StudyAids } from "@/features/summarization/components/StudyAids";

describe("StudyAids", () => {
  it("lists chapters that move the player and hides answers until asked", () => {
    const onSeek = vi.fn();
    render(
      <StudyAids
        chapters={[
          { start: 0, end: 600, title: "A crise do software" },
          { start: 1310, end: 1800, title: "A era da IA generativa" },
        ]}
        questions={[{ question: "Quantos autores teve o manifesto ágil?", answer: "17 desenvolvedores.", start: 740 }]}
        onSeek={onSeek}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Ir para 21:50" }));
    expect(onSeek).toHaveBeenCalledWith(1310);

    expect(screen.queryByText("17 desenvolvedores.")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Ver resposta"));
    expect(screen.getByText(/17 desenvolvedores\./)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ir para 12:20" }));
    expect(onSeek).toHaveBeenCalledWith(740);
  });

  it("renders nothing without chapters or questions", () => {
    const { container } = render(<StudyAids />);
    expect(container).toBeEmptyDOMElement();
  });
});
