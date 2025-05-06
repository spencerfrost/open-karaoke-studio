import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { type LucideIcon } from "lucide-react";

interface NavItem {
  name: string;
  path: string;
  icon: LucideIcon;
}

interface NavBarProps {
  items: NavItem[];
}

const NavBar: React.FC<NavBarProps> = ({ items }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path: string): boolean => {
    return location.pathname === path;
  };

  return (
    <nav className="flex justify-around py-2 bg-russet border-t-1 border-border/80 sticky bottom-0 z-20">
      {items.map((item) => {
        const active = isActive(item.path);
        const Icon = item.icon;

        return (
          <button
            key={item.name}
            onClick={() => navigate(item.path)}
            className={`flex flex-col items-center justify-center gap-1 text-background transition-all ${
              active ? "opacity-100" : "opacity-60 hover:opacity-80"
            }`}
            aria-current={active ? "page" : undefined}
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
