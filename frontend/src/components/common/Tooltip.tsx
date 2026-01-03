import React, { useState, useRef, useEffect } from 'react';
import { HelpCircle } from 'lucide-react';

interface TooltipProps {
  content: string;
  children?: React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  iconSize?: 'sm' | 'md' | 'lg';
}

const iconSizes = {
  sm: 'w-3 h-3',
  md: 'w-4 h-4',
  lg: 'w-5 h-5'
};

export function Tooltip({ 
  content, 
  children, 
  position = 'top',
  iconSize = 'sm'
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState(position);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isVisible && tooltipRef.current && triggerRef.current) {
      const tooltip = tooltipRef.current.getBoundingClientRect();
      const trigger = triggerRef.current.getBoundingClientRect();
      const viewport = {
        width: window.innerWidth,
        height: window.innerHeight
      };

      let newPosition = position;

      // Ajustar posición si se sale del viewport
      if (position === 'top' && trigger.top - tooltip.height < 0) {
        newPosition = 'bottom';
      } else if (position === 'bottom' && trigger.bottom + tooltip.height > viewport.height) {
        newPosition = 'top';
      } else if (position === 'left' && trigger.left - tooltip.width < 0) {
        newPosition = 'right';
      } else if (position === 'right' && trigger.right + tooltip.width > viewport.width) {
        newPosition = 'left';
      }

      setTooltipPosition(newPosition);
    }
  }, [isVisible, position]);

  const positionStyles = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2'
  };

  const arrowStyles = {
    top: 'top-full left-1/2 -translate-x-1/2 border-t-gray-800 border-x-transparent border-b-transparent',
    bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-gray-800 border-x-transparent border-t-transparent',
    left: 'left-full top-1/2 -translate-y-1/2 border-l-gray-800 border-y-transparent border-r-transparent',
    right: 'right-full top-1/2 -translate-y-1/2 border-r-gray-800 border-y-transparent border-l-transparent'
  };

  return (
    <div 
      className="relative inline-flex items-center"
      ref={triggerRef}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {children || (
        <HelpCircle 
          className={`${iconSizes[iconSize]} text-gray-400 hover:text-gray-600 cursor-help transition-colors`}
          tabIndex={0}
          aria-label="Información"
        />
      )}
      
      {isVisible && (
        <div 
          ref={tooltipRef}
          className={`absolute z-50 ${positionStyles[tooltipPosition]}`}
          role="tooltip"
        >
          <div className="bg-gray-800 text-white text-xs rounded-lg py-2 px-3 max-w-xs shadow-lg">
            {content}
            {/* Flecha del tooltip */}
            <div 
              className={`absolute w-0 h-0 border-4 ${arrowStyles[tooltipPosition]}`}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default Tooltip;