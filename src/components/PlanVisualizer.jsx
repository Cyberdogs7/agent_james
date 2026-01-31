import React from 'react';
import { CheckCircle, Circle, Loader2 } from 'lucide-react';

const PlanVisualizer = ({ steps = [], currentStepIndex = -1 }) => {
    if (!steps || steps.length === 0) {
        return <div className="text-sm text-purple-200/80 italic">Plan generated (details unavailable)</div>;
    }

    return (
        <div className="relative pl-2 space-y-0">
            {/* Vertical Line Container */}
            <div className="absolute left-[19px] top-4 bottom-4 w-0.5 bg-purple-500/20" />

            {steps.map((step, idx) => {
                // Determine Status
                // Priority: Explicit Status > Inferred by Index
                let status = step.status || 'PENDING';

                if (!step.status && currentStepIndex !== -1) {
                    if (idx < currentStepIndex) status = 'COMPLETED';
                    else if (idx === currentStepIndex) status = 'IN_PROGRESS';
                    else status = 'PENDING';
                }

                // Status Styles & Icons
                let Icon = Circle;
                let colorClass = "text-purple-500/40";
                let bgClass = "bg-purple-500/5";
                let textClass = "text-purple-200/60";

                if (status === 'COMPLETED' || status === 'DONE') {
                    Icon = CheckCircle;
                    colorClass = "text-green-400";
                    bgClass = "bg-green-500/10";
                    textClass = "text-green-100/80 line-through decoration-green-500/30";
                } else if (status === 'IN_PROGRESS' || status === 'RUNNING') {
                    Icon = Loader2;
                    colorClass = "text-purple-300 animate-spin";
                    bgClass = "bg-purple-500/20 border-purple-400/30";
                    textClass = "text-purple-100 font-bold";
                } else {
                    // Pending
                    textClass = "text-purple-200/90";
                }

                return (
                    <div key={idx} className="relative flex gap-4 py-2 group">
                        {/* Icon Bubble */}
                        <div className={`relative z-10 w-8 h-8 rounded-full border border-purple-500/20 ${bgClass} flex items-center justify-center shrink-0 transition-colors`}>
                            <Icon size={14} className={colorClass} />
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0 pt-1">
                            <div className={`text-sm ${textClass} transition-colors`}>
                                {step.title || step.description || `Step ${idx + 1}`}
                            </div>
                            {step.details && (
                                <div className="text-xs text-purple-200/40 mt-1 pl-1 border-l border-purple-500/10">
                                    {step.details}
                                </div>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

export default PlanVisualizer;
