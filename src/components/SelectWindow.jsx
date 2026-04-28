import React from 'react';

const SelectWindow = ({ options, onSelect, socket }) => {
    return (
        <div className="bg-black/80  text-white p-6 rounded-lg shadow-2xl border border-gold9/30 w-full max-w-md pointer-events-auto">
            <h2 className="text-xl font-bold text-gold9 mb-4 tracking-widest text-center">SELECT OPTION</h2>
            <div className="flex flex-col gap-3">
                {(options || []).map((option, index) => (
                    <button
                        key={index}
                        onClick={() => {
                            if (socket) {
                                socket.emit('user_input', { text: option });
                            }
                            if (onSelect) {
                                onSelect(option);
                            }
                        }}
                        className="px-4 py-3 bg-gold9/10 hover:bg-gold9/20 border border-gold9/50 rounded transition-all text-left flex justify-between items-center group"
                    >
                        <span className="font-mono text-sm group-hover:text-gold9 transition-colors">{option}</span>
                        <span className="text-gold9/50 text-xs opacity-0 group-hover:opacity-100 transition-opacity">SELECT</span>
                    </button>
                ))}
            </div>
        </div>
    );
};

export default SelectWindow;
