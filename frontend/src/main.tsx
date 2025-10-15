import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

createRoot(document.getElementById("root")!).render(<App />);

// Enhance navbar shadow on scroll
const nav = document.getElementById("app-nav");
if (nav) {
  const onScroll = () => {
    const y = window.scrollY || window.pageYOffset;
    if (y > 8) {
      nav.classList.add("shadow-elevated");
    } else {
      nav.classList.remove("shadow-elevated");
    }
  };
  window.addEventListener("scroll", onScroll, { passive: true });
}
