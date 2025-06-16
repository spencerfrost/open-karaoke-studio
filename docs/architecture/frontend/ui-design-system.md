# UI Design System - Open Karaoke Studio Frontend

**Last Updated**: June 15, 2025  
**Status**: Current Implementation  
**Technologies**: Tailwind CSS v4 • Shadcn/UI • CSS Custom Properties

## 🎯 Overview

The Open Karaoke Studio frontend uses a comprehensive design system built on Tailwind CSS v4 and Shadcn/UI components. The system provides a vintage-inspired color palette, consistent spacing, typography, and reusable component patterns that ensure visual cohesion across the application.

## 🎨 Design Foundation

### Color System
The application uses a vintage-inspired color palette defined through CSS custom properties and automatically available as Tailwind utilities:

```css
/* Color palette defined in index.css */
:root {
  /* Primary vintage colors */
  --black: #080705;          /* Deep black for text and borders */
  --rust: #b44819;           /* Primary brand color */
  --russet: #774320;         /* Secondary brand color */
  --lemon-chiffon: #f5f3c7;  /* Light backgrounds and highlights */
  --orange-peel: #fd9a02;    /* Accent and warning color */
  --dark-cyan: #01928b;      /* Success and info color */
  --pale-warm-beige: #c7b99c; /* Neutral backgrounds */
  
  /* Shadcn/UI design tokens */
  --background: hsl(0 0% 100%);
  --foreground: hsl(222.2 84% 4.9%);
  --primary: hsl(222.2 47.4% 11.2%);
  --primary-foreground: hsl(210 40% 98%);
  --secondary: hsl(210 40% 96%);
  --secondary-foreground: hsl(222.2 84% 4.9%);
  --muted: hsl(210 40% 96%);
  --muted-foreground: hsl(215.4 16.3% 46.9%);
  --accent: hsl(210 40% 96%);
  --accent-foreground: hsl(222.2 84% 4.9%);
  --destructive: hsl(0 84.2% 60.2%);
  --destructive-foreground: hsl(210 40% 98%);
  --border: hsl(214.3 31.8% 91.4%);
  --input: hsl(214.3 31.8% 91.4%);
  --ring: hsl(222.2 84% 4.9%);
}

/* Dark mode variants */
.dark {
  --background: hsl(222.2 84% 4.9%);
  --foreground: hsl(210 40% 98%);
  /* ... other dark mode overrides */
}
```

### Available Color Utilities
Tailwind v4 automatically generates utilities from CSS custom properties:

```typescript
// Vintage color utilities
<div className="bg-rust text-lemon-chiffon border-orange-peel">
<span className="text-russet bg-pale-warm-beige">
<button className="bg-dark-cyan hover:bg-rust transition-colors">

// Shadcn color utilities  
<div className="bg-background text-foreground border-border">
<button className="bg-primary text-primary-foreground">
<div className="bg-muted text-muted-foreground">
```

## 🧩 Component System (Shadcn/UI)

### Base Component Architecture
Shadcn/UI components serve as the foundation, providing accessible and customizable primitives:

```typescript
// Example: Button component
const Button = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>
>(({ className, variant, size, asChild = false, ...props }, ref) => {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      {...props}
    />
  );
});
```

### Component Variants
Using `class-variance-authority` for type-safe component variants:

```typescript
const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        // Custom vintage variants
        vintage: "bg-rust text-lemon-chiffon hover:bg-russet border border-orange-peel",
        accent: "bg-orange-peel text-black hover:bg-rust hover:text-lemon-chiffon",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);
```

### Core Component Library

#### Layout Components
```typescript
// Card family
import { Card, CardHeader, CardContent, CardFooter, CardTitle, CardDescription } from "@/components/ui/card";

// Dialog family
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

// Sheet family (for mobile navigation)
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
```

#### Form Components
```typescript
// Input components
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

// Selection components
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Switch } from "@/components/ui/switch";
```

#### Feedback Components
```typescript
// Status and feedback
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Toast } from "@/components/ui/toast";
```

## 📐 Typography System

### Font Stack
```css
/* Typography configuration in tailwind.config.js */
module.exports = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
};
```

### Typography Scale
```typescript
// Typography utility classes
<h1 className="scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl">
<h2 className="scroll-m-20 border-b pb-2 text-3xl font-semibold tracking-tight">
<h3 className="scroll-m-20 text-2xl font-semibold tracking-tight">
<h4 className="scroll-m-20 text-xl font-semibold tracking-tight">
<p className="leading-7 [&:not(:first-child)]:mt-6">
<blockquote className="mt-6 border-l-2 pl-6 italic">
<code className="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm font-semibold">
```

### Text Styling Patterns
```typescript
// Common text patterns used throughout the app
const textStyles = {
  // Headlines
  pageTitle: "text-3xl font-bold text-foreground",
  sectionTitle: "text-xl font-semibold text-foreground",
  cardTitle: "text-lg font-medium text-foreground",
  
  // Body text
  bodyText: "text-sm text-foreground leading-relaxed",
  captionText: "text-xs text-muted-foreground",
  
  // Interactive text
  linkText: "text-primary hover:underline cursor-pointer",
  buttonText: "text-sm font-medium",
  
  // Status text
  successText: "text-dark-cyan font-medium",
  errorText: "text-destructive font-medium",
  warningText: "text-orange-peel font-medium",
};
```

## 🎛️ Component Composition Patterns

### Song Card Example
Demonstrates how design system components compose together:

```typescript
function SongCard({ song, onSelect, variant = "default" }: SongCardProps) {
  return (
    <Card className={cn(
      "group cursor-pointer transition-all duration-200",
      "hover:shadow-md hover:shadow-orange-peel/20",
      "border-border hover:border-orange-peel/50",
      variant === "compact" && "p-2",
      variant === "featured" && "border-2 border-orange-peel bg-gradient-to-br from-lemon-chiffon to-pale-warm-beige"
    )}>
      <CardHeader className={cn(
        "pb-2",
        variant === "compact" && "pb-1"
      )}>
        <div className="flex items-center gap-3">
          <ArtworkDisplay 
            song={song} 
            size={variant === "compact" ? "sm" : "md"}
            className="rounded-md shadow-sm" 
          />
          <div className="flex-1 min-w-0">
            <CardTitle className="line-clamp-1 text-foreground group-hover:text-rust transition-colors">
              {song.title}
            </CardTitle>
            <CardDescription className="line-clamp-1">
              {song.artist}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="flex items-center justify-between">
          <SourceBadges song={song} />
          <Button 
            size="sm" 
            variant="vintage"
            onClick={() => onSelect(song)}
            className="opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <Play className="h-3 w-3 mr-1" />
            Play
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Dialog Pattern
Consistent dialog layout using design system:

```typescript
function SongDetailsDialog({ song, open, onClose }: SongDetailsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden">
        <DialogHeader className="border-b border-border pb-4">
          <DialogTitle className="text-2xl font-bold text-rust">
            {song.title}
          </DialogTitle>
          <DialogDescription className="text-lg text-muted-foreground">
            {song.artist}
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 py-4">
          <div className="space-y-4">
            <ArtworkDisplay 
              song={song} 
              size="lg" 
              className="w-full aspect-square rounded-lg shadow-lg" 
            />
          </div>
          
          <div className="space-y-4">
            <PrimarySongDetails song={song} />
          </div>
        </div>
        
        {song.lyrics && (
          <div className="border-t border-border pt-4">
            <SongLyricsSection lyrics={song.lyrics} />
          </div>
        )}
        
        <DialogFooter className="border-t border-border pt-4">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button variant="vintage" onClick={() => handlePlay(song)}>
            <Play className="h-4 w-4 mr-2" />
            Play Song
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

## 📱 Responsive Design System

### Breakpoint Strategy
```typescript
// Tailwind breakpoints consistently used
const breakpoints = {
  sm: '640px',   // Mobile landscape
  md: '768px',   // Tablet
  lg: '1024px',  // Desktop
  xl: '1280px',  // Large desktop
  '2xl': '1536px' // Extra large
};

// Usage patterns
<div className="
  grid 
  grid-cols-1         // Mobile: single column
  sm:grid-cols-2      // Tablet: two columns
  lg:grid-cols-3      // Desktop: three columns
  xl:grid-cols-4      // Large: four columns
  gap-4 
  p-4 
  lg:p-6              // Larger padding on desktop
">
```

### Mobile-First Component Patterns
```typescript
// Mobile-optimized song card
function MobileSongCard({ song }: SongCardProps) {
  return (
    <Card className="w-full">
      {/* Mobile layout optimized for touch */}
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-3">
          <ArtworkDisplay song={song} size="sm" />
          <div className="flex-1 min-w-0">
            <h3 className="font-medium truncate text-base">
              {song.title}
            </h3>
            <p className="text-sm text-muted-foreground truncate">
              {song.artist}
            </p>
          </div>
          <Button size="sm" variant="vintage">
            <Play className="h-4 w-4" />
          </Button>
        </div>
        
        {/* Additional info hidden on mobile, shown on larger screens */}
        <div className="hidden sm:flex items-center justify-between">
          <SourceBadges song={song} />
          <Badge variant="secondary">
            {formatDuration(song.duration)}
          </Badge>
        </div>
      </div>
    </Card>
  );
}
```

## 🎨 Theme System

### Dark Mode Support
```css
/* Automatic dark mode based on system preference */
@media (prefers-color-scheme: dark) {
  :root {
    --background: hsl(222.2 84% 4.9%);
    --foreground: hsl(210 40% 98%);
    /* ... other dark mode overrides */
  }
}

/* Manual dark mode toggle */
.dark {
  --background: hsl(222.2 84% 4.9%);
  --foreground: hsl(210 40% 98%);
  /* ... dark mode color scheme */
}
```

### Theme Toggle Implementation
```typescript
function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === "light" ? "dark" : "light")}
    >
      <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
}
```

## 🎭 Visual Effects System

### Vintage Texture Overlays
```css
/* CSS texture patterns for vintage aesthetic */
.vintage-texture-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0.03;
  background-image: 
    radial-gradient(circle, transparent 20%, rgba(255,255,255,0.3) 20.5%, rgba(255,255,255,0.3) 28%, transparent 28.5%),
    linear-gradient(0deg, transparent 24%, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.05) 26%, transparent 27%, transparent 74%, rgba(255,255,255,0.05) 75%, rgba(255,255,255,0.05) 76%, transparent 77%);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: 1;
}

.vintage-sunburst-pattern {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0.02;
  background: conic-gradient(from 0deg, transparent, rgba(253, 154, 2, 0.1), transparent 10deg);
  pointer-events: none;
  z-index: 1;
}
```

### Animation Patterns
```typescript
// Consistent animations using Tailwind
const animations = {
  // Loading states
  pulse: "animate-pulse",
  spin: "animate-spin",
  
  // Transitions
  fadeIn: "animate-in fade-in duration-200",
  fadeOut: "animate-out fade-out duration-200",
  slideIn: "animate-in slide-in-from-right duration-300",
  slideOut: "animate-out slide-out-to-right duration-300",
  
  // Hover effects
  hover: "transition-all duration-200 ease-in-out",
  hoverScale: "hover:scale-105 transition-transform duration-200",
  hoverShadow: "hover:shadow-lg hover:shadow-orange-peel/20 transition-shadow duration-200",
};
```

## 🧪 Design System Testing

### Visual Regression Testing
```typescript
// Storybook stories for design system components
export default {
  title: 'Design System/Button',
  component: Button,
  parameters: {
    docs: {
      description: {
        component: 'The main button component with vintage styling variants.',
      },
    },
  },
};

export const AllVariants = () => (
  <div className="space-y-4">
    <div className="flex gap-2">
      <Button variant="default">Default</Button>
      <Button variant="vintage">Vintage</Button>
      <Button variant="accent">Accent</Button>
      <Button variant="outline">Outline</Button>
    </div>
    <div className="flex gap-2">
      <Button size="sm">Small</Button>
      <Button size="default">Default</Button>
      <Button size="lg">Large</Button>
    </div>
  </div>
);
```

### Design Token Testing
```typescript
// Ensuring design tokens are properly applied
describe('Design System', () => {
  it('applies vintage colors correctly', () => {
    render(<Button variant="vintage">Test</Button>);
    const button = screen.getByRole('button');
    
    expect(button).toHaveClass('bg-rust');
    expect(button).toHaveClass('text-lemon-chiffon');
    expect(button).toHaveClass('border-orange-peel');
  });
  
  it('respects dark mode preferences', () => {
    render(
      <div className="dark">
        <Card>Test content</Card>
      </div>
    );
    
    const card = screen.getByText('Test content').closest('div');
    expect(card).toHaveClass('bg-card');
  });
});
```

## 📁 File Organization

### Design System Structure
```
src/components/ui/           # Shadcn base components
├── button.tsx
├── card.tsx
├── dialog.tsx
├── input.tsx
└── ...

src/lib/
├── utils.ts                # Class name utilities (cn function)
└── theme.ts                # Theme configuration

src/styles/
├── globals.css             # Global styles and CSS variables
└── components.css          # Component-specific styles

tailwind.config.js          # Tailwind configuration
components.json             # Shadcn component configuration
```

## 🔗 Integration Guidelines

### Adding New Components
1. **Start with Shadcn/UI** base component if available
2. **Extend with variants** using class-variance-authority
3. **Apply vintage color scheme** through CSS custom properties
4. **Ensure responsive behavior** with Tailwind breakpoints
5. **Test accessibility** with screen readers and keyboard navigation

### Custom Styling Rules
1. **Prefer Tailwind utilities** over custom CSS
2. **Use CSS custom properties** for dynamic values
3. **Maintain consistent spacing** using Tailwind scale
4. **Follow vintage color palette** for brand consistency
5. **Ensure dark mode compatibility** for all components

---

**Next Steps**: Explore the [Component Architecture](component-architecture.md) to understand how these design system elements are composed into larger application features, or check out the [Song Library Interface](components/song-library-interface.md) for a practical example of the design system in action.
