import { Moon, Sun, History, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import { Link, useLocation } from "react-router-dom";

export const Navigation = () => {
  const { theme, setTheme } = useTheme();
  const { pathname } = useLocation();

  const toggleTheme = () => {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    toast.success(newTheme === "dark" ? "🌙 Dark mode enabled" : "☀️ Light mode enabled");
  };

  const showHistory = () => {
    window.dispatchEvent(new CustomEvent('taskflow:history:toggle'));
  };

  const showAbout = () => {
    toast.info("TaskFlow v1.0 - AI-Powered Project Planning");
  };

  return (
    <nav className="glass sticky top-0 z-50 border-b border-border/50 transition-[box-shadow,height] duration-300 will-change-transform" id="app-nav">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Link to="/" className="group relative flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-gradient-primary/10 border border-primary/20 group-hover:bg-gradient-primary/20 transition-all duration-300 group-hover:scale-105">
                <img src="/taskflow.png" alt="TaskFlow" className="w-10 h-10" />
              </div>
              <div className="relative">
                <h1 className="text-2xl font-heading font-bold bg-gradient-primary bg-clip-text text-transparent">
                  TaskFlow
                </h1>
              </div>
            </Link>
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              className="hover:bg-primary/10 hover:scale-105 transition-all duration-200 rounded-xl"
            >
              {theme === "dark" ? (
                <Sun className="h-5 w-5 text-primary" />
              ) : (
                <Moon className="h-5 w-5 text-primary" />
              )}
            </Button>
            
            <Button
              variant="ghost"
              size="icon"
              onClick={showHistory}
              className="hover:bg-accent/10 hover:scale-105 transition-all duration-200 rounded-xl"
            >
              <History className="h-5 w-5 text-accent" />
            </Button>
            
            <Button
              variant="ghost"
              size="icon"
              onClick={showAbout}
              className="hover:bg-secondary/50 hover:scale-105 transition-all duration-200 rounded-xl"
            >
              <Info className="h-5 w-5 text-muted-foreground" />
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
};
