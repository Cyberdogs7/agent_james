import React from 'react';

const Suggestion = ({ suggestion, onClose }) => {
    if (!suggestion) {
        return null;
    }

    return (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-gray-800 text-white p-4 rounded-lg shadow-lg flex items-center z-50">
            <p className="mr-4">{suggestion}</p>
            <button
                onClick={onClose}
                className="text-gray-400 hover:text-white"
            >
                &times;
            </button>
        </div>
    );
};

export default Suggestion;
