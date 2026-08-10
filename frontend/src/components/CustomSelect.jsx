import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import "./CustomSelect.css";

export default function CustomSelect({ value, onChange, options, placeholder, id }) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const selectedOption = options.find((opt) => opt.value === value);
  const displayValue = selectedOption ? selectedOption.label : placeholder || "Select...";

  return (
    <div className="custom-select-container" ref={containerRef} id={id}>
      <div
        className={`form-input custom-select-trigger ${isOpen ? "open" : ""}`}
        onClick={() => setIsOpen(!isOpen)}
        tabIndex={0}
      >
        <span className="custom-select-value">{displayValue}</span>
        <ChevronDown size={16} className={`custom-select-icon ${isOpen ? "open" : ""}`} />
      </div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="custom-select-dropdown"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
          >
            {options.length > 0 ? (
              options.map((opt) => (
                <div
                  key={opt.value}
                  className={`custom-select-option ${opt.value === value ? "selected" : ""}`}
                  onClick={() => {
                    onChange({ target: { value: opt.value } });
                    setIsOpen(false);
                  }}
                >
                  {opt.label}
                </div>
              ))
            ) : (
              <div className="custom-select-option empty">No options available</div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
