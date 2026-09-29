import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { PinPad } from './PinPad';

function Harness({ onSubmit }: { onSubmit(v: string): void }) {
  const [v, setV] = useState('');
  return <PinPad value={v} onChange={setV} onSubmit={onSubmit} maxLength={4} />;
}

describe('PinPad', () => {
  it('auto-submits at max length', async () => {
    const onSubmit = vi.fn();
    render(<Harness onSubmit={onSubmit} />);
    for (const d of ['1', '2', '3', '4'])
      await userEvent.click(screen.getByRole('button', { name: `Digit ${d}` }));
    expect(onSubmit).toHaveBeenCalledWith('1234');
  });

  it('accepts a physical keyboard', async () => {
    const onSubmit = vi.fn();
    render(<Harness onSubmit={onSubmit} />);
    await userEvent.keyboard('9876');
    expect(onSubmit).toHaveBeenCalledWith('9876');
  });

  it('touch targets are at least 56px (min-h-touch)', () => {
    render(<Harness onSubmit={() => {}} />);
    expect(screen.getByRole('button', { name: 'Digit 5' }).className).toContain('min-h-touch');
  });
});
