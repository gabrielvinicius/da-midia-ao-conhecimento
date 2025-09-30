import { render, screen } from '@testing-library/react';
import { Button } from './Button';
import { describe, it, expect } from 'vitest';

describe('Button Component', () => {
  it('should render the button with the correct text', () => {
    // Arrange
    const buttonText = 'Click me';

    // Act
    render(<Button>{buttonText}</Button>);

    // Assert
    const buttonElement = screen.getByRole('button', { name: buttonText });
    expect(buttonElement).toBeInTheDocument();
  });

  it('should apply the correct default variant classes', () => {
    render(<Button>Default</Button>);
    const buttonElement = screen.getByRole('button');
    // Checks if the base classes and the default variant class are applied
    expect(buttonElement.className).toContain('bg-primary');
  });

  it('should be disabled when the disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);
    const buttonElement = screen.getByRole('button');
    expect(buttonElement).toBeDisabled();
  });
});
