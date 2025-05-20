import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { type LucideIcon } from "lucide-react";
import { Button } from "../ui/button";

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
    <nav className="flex h-18 bg-russet border-t-1 border-border/80 sticky bottom-0 z-20 gap-4 pb-4 pt-2 md:py-1">
      {items.map((item) => {
        const active = isActive(item.path);
        const Icon = item.icon;

        return (
          <Button
            key={item.name}
            variant="ghost"
            onClick={() => navigate(item.path)}
            className={`flex-1 flex flex-col items-center justify-center gap-1 text-background h-full rounded-none ${
              active ? "opacity-100" : "opacity-50"
            }`}
            aria-current={active ? "page" : undefined}
          >
            <Icon size={20} />
            <span className="text-xs mt-1">{item.name}</span>
          </Button>
        );
      })}
    </nav>
  );
};

export default NavBar;
