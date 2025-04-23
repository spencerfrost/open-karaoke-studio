import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { type LucideIcon } from "lucide-react"; // Use the specific type for Lucide icons

// Define the structure for a single navigation item
interface NavItem {
  name: string;
  path: string;
  icon: LucideIcon; // Expecting a Lucide icon component
}

// Define the props for the NavBar component
interface NavBarProps {
  /** Array of navigation item objects */
  items: NavItem[];
}

const NavBar: React.FC<NavBarProps> = ({ items }) => {
  const navigate = useNavigate();
  const location = useLocation();

  // Determine if a nav item is active
  const isActive = (path: string): boolean => {
    return location.pathname === path;
  };

  return (
    <nav className="flex justify-around py-2 bg-background border-t-1 border-border/80 sticky bottom-0 z-20">
      {items.map((item) => {
        const active = isActive(item.path);
        const Icon = item.icon;

        return (
          <button
            key={item.name}
            onClick={() => navigate(item.path)}
            className={`flex flex-col items-center justify-center gap-1 transition-all duration-200 ease-in-out ${
              active
                ? "text-foreground opacity-100"
                : "text-foreground opacity-60 hover:opacity-80"
            }`}
            aria-current={active ? "page" : undefined} // Accessibility: indicate current page
          >
            <Icon size={20} />
            <span className="text-xs mt-1">{item.name}</span>
          </button>
        );
      })}
    </nav>
  );
};

export default NavBar;
