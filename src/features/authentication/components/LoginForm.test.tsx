import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { LoginForm } from './LoginForm';
import { render } from '../../../test/test-utils'; // Use our custom render

// Mock the custom hook that handles the mutation
const mockLogin = vi.fn();
vi.mock('../hooks/useAuthMutations', () => ({
  useLogin: () => ({
    mutate: mockLogin,
    isPending: false,
  }),
}));

describe('LoginForm Component', () => {
  it('should allow a user to fill out and submit the form', async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    // Arrange: Find form elements
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    // Act: Simulate user input
    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');

    // Assert: Check if inputs have the correct values
    expect(emailInput).toHaveValue('test@example.com');
    expect(passwordInput).toHaveValue('password123');

    // Act: Simulate form submission
    await user.click(loginButton);

    // Assert: Check if the login mutation function was called with the correct data
    expect(mockLogin).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password123',
    });
  });

  it('should show validation errors for invalid input', async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    const loginButton = screen.getByRole('button', { name: /login/i });

    // Act: Submit form with empty fields
    await user.click(loginButton);

    // Assert: Check for validation messages
    expect(await screen.findByText(/invalid email address/i)).toBeInTheDocument();
    expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
  });
});
