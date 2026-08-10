import { useState, createContext, useContext } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import "./ChainOfThought.css";

const ChainOfThoughtContext = createContext();

export function ChainOfThought({ children }) {
  return (
    <div className="chain-of-thought-root">
      {children}
    </div>
  );
}

export function ChainOfThoughtStep({ children, defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <ChainOfThoughtContext.Provider value={{ isOpen, setIsOpen }}>
      <div className="chain-of-thought-step">
        <div className="chain-of-thought-timeline">
          <div className="chain-of-thought-dot" />
          <div className="chain-of-thought-line" />
        </div>
        <div className="chain-of-thought-content-area">
          {children}
        </div>
      </div>
    </ChainOfThoughtContext.Provider>
  );
}

export function ChainOfThoughtTrigger({ children }) {
  const { isOpen, setIsOpen } = useContext(ChainOfThoughtContext);
  
  return (
    <button 
      className="chain-of-thought-trigger" 
      onClick={() => setIsOpen(!isOpen)}
      type="button"
    >
      <span className="chain-of-thought-trigger-text">{children}</span>
      <ChevronDown 
        size={14} 
        className={`chain-of-thought-icon ${isOpen ? "open" : ""}`} 
      />
    </button>
  );
}

export function ChainOfThoughtContent({ children }) {
  const { isOpen } = useContext(ChainOfThoughtContext);
  
  return (
    <AnimatePresence initial={false}>
      {isOpen && (
        <motion.div
          className="chain-of-thought-content-wrapper"
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          <div className="chain-of-thought-content">
            {children}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function ChainOfThoughtItem({ children }) {
  return (
    <div className="chain-of-thought-item">
      <span className="chain-of-thought-item-text">{children}</span>
    </div>
  );
}
