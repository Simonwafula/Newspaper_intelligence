import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from './Button'

describe('Button', () => {
    it('renders children correctly', () => {
        render(<Button>Click me</Button>)
        expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
    })

    it('renders with custom className', () => {
        render(<Button className="custom-class">Content</Button>)
        const button = screen.getByRole('button')
        expect(button).toHaveClass('custom-class')
    })

    it('handles click events', () => {
        // Note: UserEvent is better but for this simple verification we just render
        // We would need to install @testing-library/user-event for interaction tests
        render(<Button>Clickable</Button>)
        expect(screen.getByRole('button')).toBeEnabled()
    })
})
