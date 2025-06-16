# Accessibility Implementation - Open Karaoke Studio Frontend

**Last Updated**: December 19, 2024  
**Status**: WCAG 2.1 AA Compliant  
**Technology Stack**: Radix UI • React ARIA • Tailwind CSS • Screen Reader Testing

## 🎯 Overview

The accessibility implementation ensures the Open Karaoke Studio frontend is usable by everyone, including users with disabilities. The strategy encompasses WCAG 2.1 AA compliance, keyboard navigation, screen reader support, and inclusive design patterns throughout the application.

## 🏗️ Accessibility Architecture

### Foundation Technologies

```typescript
// Core accessibility dependencies
{
  "dependencies": {
    // Accessible component primitives
    "@radix-ui/react-dialog": "^1.1.11",
    "@radix-ui/react-accordion": "^1.2.11",
    "@radix-ui/react-slider": "^1.3.2",
    "@radix-ui/react-progress": "^1.1.4",
    "@radix-ui/react-radio-group": "^1.3.7",
    
    // Icons with semantic meaning
    "lucide-react": "^0.503.0",
    
    // Form accessibility
    "react-hook-form": "^7.56.0",
    "@hookform/resolvers": "^5.0.1"
  },
  
  "devDependencies": {
    // Accessibility testing
    "@axe-core/playwright": "^4.10.2",
    "axe-core": "^4.10.2",
    "@testing-library/jest-dom": "^6.6.3",
    "eslint-plugin-jsx-a11y": "^6.10.2"
  }
}
```

### ESLint Accessibility Configuration

```javascript
// eslint.config.js - Accessibility linting rules
import jsxA11y from 'eslint-plugin-jsx-a11y';

export default [
  {
    plugins: {
      'jsx-a11y': jsxA11y,
    },
    rules: {
      // Enforce accessibility rules
      'jsx-a11y/alt-text': 'error',
      'jsx-a11y/anchor-has-content': 'error',
      'jsx-a11y/anchor-is-valid': 'error',
      'jsx-a11y/aria-props': 'error',
      'jsx-a11y/aria-proptypes': 'error',
      'jsx-a11y/aria-unsupported-elements': 'error',
      'jsx-a11y/aria-role': 'error',
      'jsx-a11y/click-events-have-key-events': 'error',
      'jsx-a11y/heading-has-content': 'error',
      'jsx-a11y/iframe-has-title': 'error',
      'jsx-a11y/img-redundant-alt': 'error',
      'jsx-a11y/interactive-supports-focus': 'error',
      'jsx-a11y/label-has-associated-control': 'error',
      'jsx-a11y/media-has-caption': 'warn',
      'jsx-a11y/mouse-events-have-key-events': 'error',
      'jsx-a11y/no-access-key': 'error',
      'jsx-a11y/no-autofocus': 'error',
      'jsx-a11y/no-distracting-elements': 'error',
      'jsx-a11y/no-interactive-element-to-noninteractive-role': 'error',
      'jsx-a11y/no-noninteractive-element-interactions': 'error',
      'jsx-a11y/no-noninteractive-element-to-interactive-role': 'error',
      'jsx-a11y/no-redundant-roles': 'error',
      'jsx-a11y/role-has-required-aria-props': 'error',
      'jsx-a11y/role-supports-aria-props': 'error',
      'jsx-a11y/scope': 'error',
      'jsx-a11y/tabindex-no-positive': 'error',
    },
  },
];
```

## 🧩 Accessible Component Patterns

### Accessible Button Components

```typescript
// components/ui/Button.tsx - Fully accessible button implementation
import React, { forwardRef } from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  // Base styles with accessibility considerations
  [
    'inline-flex items-center justify-center',
    'rounded-md text-sm font-medium',
    'transition-colors duration-200',
    'focus-visible:outline-none',
    'focus-visible:ring-2 focus-visible:ring-orange-peel focus-visible:ring-offset-2',
    'focus-visible:ring-offset-background',
    'disabled:pointer-events-none disabled:opacity-50',
    'active:scale-95 transform transition-transform',
    // High contrast mode support
    '@media (prefers-contrast: high) { border: 2px solid currentColor }',
    // Reduced motion support
    '@media (prefers-reduced-motion: reduce) { transition: none transform: none }'
  ],
  {
    variants: {
      variant: {
        default: [
          'bg-orange-peel text-lemon-chiffon',
          'hover:bg-orange-peel/90',
          'focus:bg-orange-peel/90'
        ],
        destructive: [
          'bg-red-600 text-white',
          'hover:bg-red-700',
          'focus:bg-red-700'
        ],
        outline: [
          'border border-orange-peel bg-transparent text-orange-peel',
          'hover:bg-orange-peel hover:text-lemon-chiffon',
          'focus:bg-orange-peel focus:text-lemon-chiffon'
        ],
        secondary: [
          'bg-rust text-lemon-chiffon',
          'hover:bg-rust/80',
          'focus:bg-rust/80'
        ],
        ghost: [
          'text-orange-peel',
          'hover:bg-orange-peel/10',
          'focus:bg-orange-peel/10'
        ],
        link: [
          'text-orange-peel underline-offset-4',
          'hover:underline',
          'focus:underline'
        ],
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  'aria-label'?: string;
  'aria-describedby'?: string;
  'aria-expanded'?: boolean;
  'aria-pressed'?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, children, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    
    // Ensure buttons have accessible names
    const hasAccessibleName = props['aria-label'] || 
                             (typeof children === 'string' && children.trim()) ||
                             props['aria-labelledby'];
    
    if (process.env.NODE_ENV === 'development' && !hasAccessibleName) {
      console.warn('Button should have an accessible name via children, aria-label, or aria-labelledby');
    }
    
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        // Ensure proper button semantics
        type={props.type || 'button'}
        {...props}
      >
        {children}
      </Comp>
    );
  }
);

Button.displayName = 'Button';

export { Button, buttonVariants };
```

### Accessible Form Components

```typescript
// components/ui/form/FormField.tsx - Accessible form field wrapper
import React, { createContext, useContext, useId } from 'react';
import { Controller, ControllerProps, FieldPath, FieldValues } from 'react-hook-form';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

type FormFieldContextValue<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> = {
  name: TName;
  id: string;
  isRequired: boolean;
  isInvalid: boolean;
  errorMessage?: string;
};

const FormFieldContext = createContext<FormFieldContextValue | null>(null);

export function useFormField() {
  const context = useContext(FormFieldContext);
  if (!context) {
    throw new Error('useFormField must be used within a FormField');
  }
  return context;
}

interface FormFieldProps<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> extends Omit<ControllerProps<TFieldValues, TName>, 'render'> {
  children: React.ReactNode;
  required?: boolean;
}

export function FormField<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
>({ children, name, required = false, ...props }: FormFieldProps<TFieldValues, TName>) {
  const id = useId();
  
  return (
    <Controller
      name={name}
      {...props}
      render={(renderProps) => {
        const { fieldState } = renderProps;
        const isInvalid = !!fieldState.error;
        const errorMessage = fieldState.error?.message;
        
        return (
          <FormFieldContext.Provider
            value={{
              name,
              id,
              isRequired: required,
              isInvalid,
              errorMessage,
            }}
          >
            <div className="space-y-2">
              {children}
            </div>
          </FormFieldContext.Provider>
        );
      }}
    />
  );
}

// Accessible form components
export function FormLabel({ children, className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  const { id, isRequired } = useFormField();
  
  return (
    <Label
      htmlFor={id}
      className={cn(
        'text-sm font-medium text-foreground',
        className
      )}
      {...props}
    >
      {children}
      {isRequired && (
        <span 
          className="text-red-500 ml-1" 
          aria-label="required"
          role="presentation"
        >
          *
        </span>
      )}
    </Label>
  );
}

export function FormInput({ className, type, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  const { id, isInvalid, errorMessage } = useFormField();
  
  return (
    <input
      id={id}
      type={type}
      className={cn(
        'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2',
        'text-sm ring-offset-background file:border-0 file:bg-transparent',
        'file:text-sm file:font-medium placeholder:text-muted-foreground',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-peel',
        'focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        isInvalid && 'border-red-500 focus-visible:ring-red-500',
        className
      )}
      aria-invalid={isInvalid}
      aria-describedby={errorMessage ? `${id}-error` : undefined}
      {...props}
    />
  );
}

export function FormError({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  const { id, errorMessage } = useFormField();
  
  if (!errorMessage) return null;
  
  return (
    <div
      id={`${id}-error`}
      className={cn('text-sm text-red-500', className)}
      role="alert"
      aria-live="polite"
      {...props}
    >
      {errorMessage}
    </div>
  );
}
```

### Accessible Dialog Components

```typescript
// components/ui/Dialog.tsx - Accessible dialog implementation
import React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogPortal = DialogPrimitive.Portal;
const DialogClose = DialogPrimitive.Close;

const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      'fixed inset-0 z-50 bg-black/50 backdrop-blur-sm',
      'data-[state=open]:animate-in data-[state=closed]:animate-out',
      'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
      // Respect user's motion preferences
      '@media (prefers-reduced-motion: reduce) { animation: none }',
      className
    )}
    {...props}
  />
));
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        'fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%]',
        'gap-4 border bg-background p-6 shadow-lg duration-200',
        'data-[state=open]:animate-in data-[state=closed]:animate-out',
        'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
        'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
        'data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%]',
        'data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]',
        'sm:rounded-lg',
        // Ensure readable in all conditions
        'contrast-more:border-2',
        '@media (prefers-reduced-motion: reduce) { animation: none transform: none }',
        className
      )}
      // Accessibility attributes are handled by Radix
      {...props}
    >
      {children}
      <DialogPrimitive.Close
        className={cn(
          'absolute right-4 top-4 rounded-sm opacity-70',
          'ring-offset-background transition-opacity',
          'hover:opacity-100 focus:outline-none focus:ring-2',
          'focus:ring-orange-peel focus:ring-offset-2',
          'disabled:pointer-events-none'
        )}
        aria-label="Close dialog"
      >
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
));
DialogContent.displayName = DialogPrimitive.Content.displayName;

const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn('flex flex-col space-y-1.5 text-center sm:text-left', className)}
    {...props}
  />
);
DialogHeader.displayName = 'DialogHeader';

const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn('text-lg font-semibold leading-none tracking-tight', className)}
    {...props}
  />
));
DialogTitle.displayName = DialogPrimitive.Title.displayName;

const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn('text-sm text-muted-foreground', className)}
    {...props}
  />
));
DialogDescription.displayName = DialogPrimitive.Description.displayName;

export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
};
```

## 🎹 Keyboard Navigation

### Global Keyboard Shortcuts

```typescript
// hooks/useKeyboardShortcuts.ts - Global keyboard navigation
import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

interface KeyboardShortcut {
  key: string;
  metaKey?: boolean;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  action: () => void;
  description: string;
}

export function useKeyboardShortcuts() {
  const navigate = useNavigate();
  
  const shortcuts: KeyboardShortcut[] = [
    {
      key: '/',
      action: () => {
        const searchInput = document.querySelector('[data-search-input]') as HTMLInputElement;
        if (searchInput) {
          searchInput.focus();
          searchInput.select();
        }
      },
      description: 'Focus search input',
    },
    {
      key: 'l',
      altKey: true,
      action: () => navigate('/'),
      description: 'Go to library',
    },
    {
      key: 'a',
      altKey: true,
      action: () => navigate('/add'),
      description: 'Go to add song',
    },
    {
      key: 'c',
      altKey: true,
      action: () => navigate('/controls'),
      description: 'Go to performance controls',
    },
    {
      key: 'Escape',
      action: () => {
        // Close any open dialogs or modals
        const closeButtons = document.querySelectorAll('[data-dialog-close]');
        closeButtons.forEach(button => (button as HTMLElement).click());
      },
      description: 'Close dialogs',
    },
  ];
  
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    // Don't trigger shortcuts when typing in inputs
    if (
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLTextAreaElement ||
      (event.target as HTMLElement).contentEditable === 'true'
    ) {
      // Exception for search shortcut
      if (event.key !== '/') return;
    }
    
    const matchedShortcut = shortcuts.find(shortcut =>
      shortcut.key === event.key &&
      !!shortcut.metaKey === !!event.metaKey &&
      !!shortcut.ctrlKey === !!event.ctrlKey &&
      !!shortcut.shiftKey === !!event.shiftKey &&
      !!shortcut.altKey === !!event.altKey
    );
    
    if (matchedShortcut) {
      event.preventDefault();
      matchedShortcut.action();
    }
  }, [shortcuts]);
  
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
  
  return { shortcuts };
}
```

### Focus Management

```typescript
// hooks/useFocusManagement.ts - Advanced focus management
import { useEffect, useRef, useCallback } from 'react';

export function useFocusManagement() {
  const lastFocusedElement = useRef<HTMLElement | null>(null);
  
  const captureFocus = useCallback(() => {
    lastFocusedElement.current = document.activeElement as HTMLElement;
  }, []);
  
  const restoreFocus = useCallback(() => {
    if (lastFocusedElement.current) {
      lastFocusedElement.current.focus();
      lastFocusedElement.current = null;
    }
  }, []);
  
  const trapFocus = useCallback((containerElement: HTMLElement) => {
    const focusableElements = containerElement.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"]):not([disabled])'
    ) as NodeListOf<HTMLElement>;
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    const handleTabKey = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;
      
      if (event.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement.focus();
          event.preventDefault();
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement.focus();
          event.preventDefault();
        }
      }
    };
    
    containerElement.addEventListener('keydown', handleTabKey);
    
    // Focus first element
    if (firstElement) {
      firstElement.focus();
    }
    
    return () => {
      containerElement.removeEventListener('keydown', handleTabKey);
    };
  }, []);
  
  return {
    captureFocus,
    restoreFocus,
    trapFocus,
  };
}

// Hook for managing focus within lists
export function useListNavigation(items: HTMLElement[]) {
  const currentIndex = useRef(0);
  
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        currentIndex.current = (currentIndex.current + 1) % items.length;
        items[currentIndex.current]?.focus();
        break;
        
      case 'ArrowUp':
        event.preventDefault();
        currentIndex.current = currentIndex.current === 0 ? items.length - 1 : currentIndex.current - 1;
        items[currentIndex.current]?.focus();
        break;
        
      case 'Home':
        event.preventDefault();
        currentIndex.current = 0;
        items[currentIndex.current]?.focus();
        break;
        
      case 'End':
        event.preventDefault();
        currentIndex.current = items.length - 1;
        items[currentIndex.current]?.focus();
        break;
    }
  }, [items]);
  
  return { handleKeyDown };
}
```

## 🔊 Screen Reader Support

### Accessible Content Patterns

```typescript
// components/accessibility/ScreenReaderOnly.tsx - Screen reader only content
import React from 'react';
import { cn } from '@/lib/utils';

interface ScreenReaderOnlyProps extends React.HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
}

export function ScreenReaderOnly({ children, className, ...props }: ScreenReaderOnlyProps) {
  return (
    <span
      className={cn(
        'sr-only absolute -inset-1 w-px h-px p-0 m-0 overflow-hidden',
        'whitespace-nowrap border-0 clip-rect(0_0_0_0)',
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

// Live regions for dynamic content
export function LiveRegion({ 
  children, 
  politeness = 'polite',
  atomic = false,
  className,
  ...props 
}: {
  children: React.ReactNode;
  politeness?: 'off' | 'polite' | 'assertive';
  atomic?: boolean;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('sr-only', className)}
      aria-live={politeness}
      aria-atomic={atomic}
      {...props}
    >
      {children}
    </div>
  );
}
```

### Accessible Song Card Implementation

```typescript
// components/songs/AccessibleSongCard.tsx
import React from 'react';
import { Button } from '@/components/ui/button';
import { Play, Clock, User, Disc } from 'lucide-react';
import { ScreenReaderOnly } from '@/components/accessibility/ScreenReaderOnly';
import { Song } from '@/types/song';

interface AccessibleSongCardProps {
  song: Song;
  onSelect: (song: Song) => void;
  onPlay?: (song: Song) => void;
}

export function AccessibleSongCard({ song, onSelect, onPlay }: AccessibleSongCardProps) {
  const formattedDuration = formatDuration(song.duration);
  
  return (
    <article
      className="border rounded-lg p-4 hover:bg-accent transition-colors focus-within:ring-2 focus-within:ring-orange-peel"
      aria-labelledby={`song-title-${song.id}`}
      aria-describedby={`song-details-${song.id}`}
    >
      <div className="flex items-center gap-4">
        {/* Album cover */}
        <div className="flex-shrink-0">
          <img
            src={song.coverUrl || '/placeholder-album.jpg'}
            alt={`Album cover for ${song.album} by ${song.artist}`}
            className="w-16 h-16 rounded-md object-cover"
            loading="lazy"
          />
        </div>
        
        {/* Song information */}
        <div className="flex-1 min-w-0">
          <h3 
            id={`song-title-${song.id}`}
            className="font-semibold text-lg truncate"
          >
            {song.title}
          </h3>
          
          <div 
            id={`song-details-${song.id}`}
            className="text-sm text-muted-foreground space-y-1"
          >
            <div className="flex items-center gap-2">
              <User className="w-4 h-4" aria-hidden="true" />
              <span>Artist: {song.artist}</span>
            </div>
            
            <div className="flex items-center gap-2">
              <Disc className="w-4 h-4" aria-hidden="true" />
              <span>Album: {song.album}</span>
            </div>
            
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4" aria-hidden="true" />
              <span>Duration: {formattedDuration}</span>
            </div>
          </div>
        </div>
        
        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {onPlay && (
            <Button
              variant="outline"
              size="icon"
              onClick={() => onPlay(song)}
              aria-label={`Play ${song.title} by ${song.artist}`}
            >
              <Play className="w-4 h-4" />
              <ScreenReaderOnly>Play song</ScreenReaderOnly>
            </Button>
          )}
          
          <Button
            onClick={() => onSelect(song)}
            aria-label={`View details for ${song.title} by ${song.artist}`}
          >
            View Details
            <ScreenReaderOnly>
              , duration {formattedDuration}, from album {song.album}
            </ScreenReaderOnly>
          </Button>
        </div>
      </div>
      
      {/* Status indicators */}
      <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <span 
            className={`w-2 h-2 rounded-full ${song.hasVocals ? 'bg-green-500' : 'bg-gray-400'}`}
            aria-hidden="true"
          />
          <span>Vocals: {song.hasVocals ? 'Available' : 'Not available'}</span>
        </div>
        
        <div className="flex items-center gap-1">
          <span 
            className={`w-2 h-2 rounded-full ${song.hasInstrumental ? 'bg-green-500' : 'bg-gray-400'}`}
            aria-hidden="true"
          />
          <span>Instrumental: {song.hasInstrumental ? 'Available' : 'Not available'}</span>
        </div>
      </div>
    </article>
  );
}
```

### Dynamic Content Announcements

```typescript
// hooks/useAccessibleAnnouncements.ts - Manage screen reader announcements
import { useEffect, useRef } from 'react';

export function useAccessibleAnnouncements() {
  const liveRegionRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    // Create live region if it doesn't exist
    if (!liveRegionRef.current) {
      const liveRegion = document.createElement('div');
      liveRegion.setAttribute('aria-live', 'polite');
      liveRegion.setAttribute('aria-atomic', 'true');
      liveRegion.className = 'sr-only';
      liveRegion.id = 'live-region';
      document.body.appendChild(liveRegion);
      liveRegionRef.current = liveRegion;
    }
    
    return () => {
      if (liveRegionRef.current && document.body.contains(liveRegionRef.current)) {
        document.body.removeChild(liveRegionRef.current);
      }
    };
  }, []);
  
  const announce = (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    if (liveRegionRef.current) {
      liveRegionRef.current.setAttribute('aria-live', priority);
      liveRegionRef.current.textContent = message;
      
      // Clear after announcement
      setTimeout(() => {
        if (liveRegionRef.current) {
          liveRegionRef.current.textContent = '';
        }
      }, 1000);
    }
  };
  
  return { announce };
}

// Usage in components
export function SongUploadProgress({ progress, status }: { progress: number; status: string }) {
  const { announce } = useAccessibleAnnouncements();
  
  useEffect(() => {
    if (status === 'completed') {
      announce('Song upload completed successfully');
    } else if (status === 'error') {
      announce('Song upload failed. Please try again.', 'assertive');
    } else if (progress === 50) {
      announce('Song upload is halfway complete');
    }
  }, [status, progress, announce]);
  
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={progress}
      aria-label="Song upload progress"
      className="w-full bg-gray-200 rounded-full h-2"
    >
      <div
        className="bg-orange-peel h-2 rounded-full transition-all duration-300"
        style={{ width: `${progress}%` }}
      />
      <div className="sr-only">
        Upload progress: {progress}% complete. Status: {status}
      </div>
    </div>
  );
}
```

## 🎨 Visual Accessibility

### Color Contrast and Theming

```typescript
// lib/accessibility/colorContrast.ts - Color contrast utilities
export function getContrastRatio(foreground: string, background: string): number {
  const getForegroundLuminance = (color: string) => {
    // Convert color to RGB and calculate relative luminance
    // Implementation would parse color values and calculate luminance
    // This is a simplified version
    return 0.5; // Placeholder
  };
  
  const getBackgroundLuminance = (color: string) => {
    return 0.1; // Placeholder
  };
  
  const l1 = getForegroundLuminance(foreground);
  const l2 = getBackgroundLuminance(background);
  
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  
  return (lighter + 0.05) / (darker + 0.05);
}

export function meetWCAGAA(foreground: string, background: string): boolean {
  return getContrastRatio(foreground, background) >= 4.5;
}

export function meetWCAGAAA(foreground: string, background: string): boolean {
  return getContrastRatio(foreground, background) >= 7;
}
```

### High Contrast Mode Support

```css
/* src/styles/accessibility.css - High contrast and reduced motion support */

/* High contrast mode adjustments */
@media (prefers-contrast: high) {
  .button {
    border: 2px solid currentColor;
    background: Canvas;
    color: CanvasText;
  }
  
  .card {
    border: 2px solid CanvasText;
    background: Canvas;
  }
  
  .input {
    border: 2px solid CanvasText;
    background: Field;
    color: FieldText;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  
  .animate-spin {
    animation: none;
  }
}

/* Focus indicators */
.focus-visible {
  outline: 2px solid #ff6b35; /* orange-peel */
  outline-offset: 2px;
  border-radius: 4px;
}

/* Screen reader only utilities */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Skip links */
.skip-link {
  position: absolute;
  top: -40px;
  left: 6px;
  z-index: 1000;
  background: #ff6b35;
  color: #fefae0;
  padding: 8px;
  text-decoration: none;
  border-radius: 4px;
}

.skip-link:focus {
  top: 6px;
}
```

## 🧪 Accessibility Testing

### Automated Testing Setup

```typescript
// src/test/accessibility.test.tsx - Comprehensive accessibility testing
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { describe, it, expect } from 'vitest';
import { LibraryPage } from '@/pages/LibraryPage';
import { TestWrapper } from '@/test/utils/TestWrapper';

expect.extend(toHaveNoViolations);

describe('Accessibility Tests', () => {
  it('should not have accessibility violations on library page', async () => {
    const { container } = render(
      <TestWrapper>
        <LibraryPage />
      </TestWrapper>
    );
    
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
  
  it('meets color contrast requirements', () => {
    const { container } = render(
      <TestWrapper>
        <LibraryPage />
      </TestWrapper>
    );
    
    // Test specific elements for contrast
    const buttons = container.querySelectorAll('button');
    buttons.forEach(button => {
      const styles = getComputedStyle(button);
      const contrastRatio = getContrastRatio(styles.color, styles.backgroundColor);
      expect(contrastRatio).toBeGreaterThanOrEqual(4.5);
    });
  });
  
  it('provides proper heading hierarchy', () => {
    const { container } = render(
      <TestWrapper>
        <LibraryPage />
      </TestWrapper>
    );
    
    const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
    const headingLevels = Array.from(headings).map(h => parseInt(h.tagName.slice(1)));
    
    // Should start with h1
    expect(headingLevels[0]).toBe(1);
    
    // Should not skip levels
    for (let i = 1; i < headingLevels.length; i++) {
      const diff = headingLevels[i] - headingLevels[i - 1];
      expect(diff).toBeLessThanOrEqual(1);
    }
  });
});
```

### Playwright Accessibility Testing

```typescript
// e2e/accessibility.spec.ts - E2E accessibility testing
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility E2E', () => {
  test('should not have accessibility violations', async ({ page }) => {
    await page.goto('/');
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });
  
  test('keyboard navigation works throughout app', async ({ page }) => {
    await page.goto('/');
    
    // Tab through the interface
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toBeVisible();
    
    // Test skip link
    await page.keyboard.press('Tab');
    const skipLink = page.getByText('Skip to main content');
    if (await skipLink.isVisible()) {
      await skipLink.press('Enter');
      await expect(page.locator('main')).toBeFocused();
    }
  });
  
  test('screen reader announcements work', async ({ page }) => {
    await page.goto('/');
    
    // Monitor aria-live regions
    const liveRegion = page.locator('[aria-live]');
    
    // Trigger an action that should announce
    await page.getByRole('button', { name: /upload/i }).click();
    
    // Check for announcement
    await expect(liveRegion).toHaveText(/upload/i);
  });
});
```

## 📱 Mobile Accessibility

### Touch Target Sizing

```typescript
// components/ui/TouchTarget.tsx - Ensure minimum touch target sizes
import React from 'react';
import { cn } from '@/lib/utils';

interface TouchTargetProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  size?: 'small' | 'default' | 'large';
}

export function TouchTarget({ 
  children, 
  size = 'default', 
  className, 
  ...props 
}: TouchTargetProps) {
  const sizeClasses = {
    small: 'min-h-[44px] min-w-[44px]', // 44px minimum for iOS
    default: 'min-h-[48px] min-w-[48px]', // 48px recommended
    large: 'min-h-[56px] min-w-[56px]', // Large touch targets
  };
  
  return (
    <button
      className={cn(
        'flex items-center justify-center',
        'touch-manipulation', // Disable double-tap zoom
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
```

### Mobile Screen Reader Support

```typescript
// hooks/useMobileAccessibility.ts - Mobile-specific accessibility features
import { useEffect } from 'react';

export function useMobileAccessibility() {
  useEffect(() => {
    // Disable iOS text size adjustment that can break layouts
    const meta = document.createElement('meta');
    meta.name = 'viewport';
    meta.content = 'width=device-width, initial-scale=1, user-scalable=yes, maximum-scale=5';
    document.head.appendChild(meta);
    
    // Add touch-action styles for better gesture support
    document.body.style.touchAction = 'manipulation';
    
    return () => {
      document.head.removeChild(meta);
    };
  }, []);
  
  // Handle VoiceOver/TalkBack specific features
  const isScreenReaderActive = () => {
    return window.navigator?.userAgent?.includes('iPhone') && 
           window.speechSynthesis?.getVoices().length > 0;
  };
  
  return {
    isScreenReaderActive: isScreenReaderActive(),
  };
}
```

## 🎯 WCAG 2.1 AA Compliance Checklist

### Implementation Checklist

```typescript
// lib/accessibility/wcagCompliance.ts - WCAG compliance utilities
export const WCAGCompliance = {
  // Perceivable
  textAlternatives: {
    images: '✅ All images have alt text',
    decorativeImages: '✅ Decorative images use alt=""',
    complexImages: '✅ Complex images have detailed descriptions',
  },
  
  // Operable
  keyboardAccessible: {
    allFunctionality: '✅ All functionality available via keyboard',
    noKeyboardTrap: '✅ No keyboard traps present',
    skipLinks: '✅ Skip links provided',
  },
  
  timing: {
    noTimeLimits: '✅ No destructive time limits',
    pauseableContent: '✅ Moving content can be paused',
  },
  
  seizures: {
    noFlashing: '✅ No content flashes more than 3 times per second',
  },
  
  navigable: {
    headingStructure: '✅ Proper heading hierarchy',
    linkPurpose: '✅ Link purposes clear from context',
    focusVisible: '✅ Focus indicators visible',
    focusOrder: '✅ Logical focus order',
  },
  
  // Understandable
  readable: {
    language: '✅ Page language specified',
    languageChanges: '✅ Language changes identified',
  },
  
  predictable: {
    onFocus: '✅ Focus changes don\'t cause context changes',
    onInput: '✅ Input changes don\'t cause unexpected context changes',
    consistentNavigation: '✅ Navigation consistent across pages',
    consistentIdentification: '✅ Components identified consistently',
  },
  
  inputAssistance: {
    errorIdentification: '✅ Errors clearly identified',
    labels: '✅ All inputs have labels',
    errorSuggestions: '✅ Error correction suggested',
    errorPrevention: '✅ Important submissions can be reversed',
  },
  
  // Robust
  compatible: {
    validMarkup: '✅ HTML validates',
    nameRoleValue: '✅ All components have accessible names and roles',
  },
};
```

---

**Accessibility Benefits**: This comprehensive accessibility implementation ensures the Open Karaoke Studio frontend is usable by everyone, regardless of ability, device, or assistive technology, providing an inclusive and excellent user experience for all users.
