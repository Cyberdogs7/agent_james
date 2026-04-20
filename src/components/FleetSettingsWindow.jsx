import React, { useState, useEffect } from 'react';
import { X, Plus, Trash2, Edit2, Save, Key, Server, Hash } from 'lucide-react';

const FleetSettingsWindow = ({ socket, onClose }) => {
    const [accounts, setAccounts] = useState([]);
    const [isAdding, setIsAdding] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [error, setError] = useState(null);

    // Form states
    const [formData, setFormData] = useState({
        name: '',
        api_key: '',
        concurrent_sessions_limit: '',
        total_sessions_limit: ''
    });

    useEffect(() => {
        if (!socket) return;

        socket.emit('get_accounts');

        const handleAccountsUpdate = (data) => {
            setAccounts(data);
            setIsAdding(false);
            setEditingId(null);
            setError(null);
        };

        const handleError = (data) => {
            setError(data.message);
        };

        socket.on('accounts_update', handleAccountsUpdate);
        socket.on('account_error', handleError);

        return () => {
            socket.off('accounts_update', handleAccountsUpdate);
            socket.off('account_error', handleError);
        };
    }, [socket]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleAddClick = () => {
        setFormData({
            name: '',
            api_key: '',
            concurrent_sessions_limit: '',
            total_sessions_limit: ''
        });
        setIsAdding(true);
        setEditingId(null);
        setError(null);
    };

    const handleEditClick = (account) => {
        setFormData({
            name: account.name || '',
            api_key: account.api_key || '',
            concurrent_sessions_limit: account.concurrent_sessions_limit || '',
            total_sessions_limit: account.total_sessions_limit || ''
        });
        setEditingId(account.id);
        setIsAdding(false);
        setError(null);
    };

    const handleSave = () => {
        setError(null);
        const payload = {
            name: formData.name,
            api_key: formData.api_key,
            concurrent_sessions_limit: formData.concurrent_sessions_limit ? parseInt(formData.concurrent_sessions_limit, 10) : null,
            total_sessions_limit: formData.total_sessions_limit ? parseInt(formData.total_sessions_limit, 10) : null
        };

        if (isAdding) {
            socket.emit('add_account', payload);
        } else if (editingId) {
            socket.emit('update_account', { id: editingId, ...payload });
        }
    };

    const handleDelete = (id) => {
        if (window.confirm("Are you sure you want to remove this account?")) {
            socket.emit('delete_account', { id });
        }
    };

    const handleCancel = () => {
        setIsAdding(false);
        setEditingId(null);
        setError(null);
    };

    const showForm = isAdding || editingId !== null;

    return (
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-black/95 border border-gold9/50 rounded-xl z-50 w-[800px] h-[600px] flex flex-col backdrop-blur-2xl shadow-[0_0_50px_rgba(255,215,0,0.15)] overflow-hidden">
            {/* Header */}
            <div className="flex-none p-4 border-b border-gold9/30 bg-gradient-to-r from-gray-900/50 to-black/50 flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <Server className="text-gold9" size={20} />
                    <h2 className="text-gold9 font-bold tracking-wider text-lg">Fleet Accounts</h2>
                </div>
                <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                    <X size={20} />
                </button>
            </div>

            {/* Content Area */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Side: List */}
                <div className="w-1/2 border-r border-gold9/20 overflow-y-auto p-4 custom-scrollbar">
                    <button
                        onClick={handleAddClick}
                        disabled={showForm && isAdding}
                        className="w-full mb-4 flex items-center justify-center gap-2 py-2 px-4 bg-gold9/10 hover:bg-gold9/20 text-gold9 border border-gold9/30 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Plus size={16} /> Add New Account
                    </button>

                    <div className="space-y-2">
                        {accounts.length === 0 ? (
                            <div className="text-center text-gray-500 py-8 italic text-sm">No accounts found.</div>
                        ) : (
                            accounts.map(acc => (
                                <div
                                    key={acc.id}
                                    className={`group relative p-3 rounded-lg border transition-all cursor-pointer hover:border-gold9/50
                                        ${editingId === acc.id ? 'bg-gold9/10 border-gold9' : 'bg-gray-900/50 border-gray-800'}`}
                                    onClick={() => handleEditClick(acc)}
                                >
                                    <div className="flex justify-between items-start mb-1">
                                        <div className="font-semibold text-white truncate pr-6">{acc.name || 'Unnamed Account'}</div>
                                    </div>
                                    <div className="text-xs text-gray-400 font-mono truncate">{acc.api_key.substring(0, 10)}...</div>
                                    <div className="mt-2 flex gap-3 text-xs text-gold9/60">
                                        <span title="Concurrent Limit" className="flex items-center gap-1">
                                            <Hash size={12} /> {acc.concurrent_sessions_limit || '∞'}
                                        </span>
                                        <span title="Total Limit" className="flex items-center gap-1">
                                            <Server size={12} /> {acc.total_sessions_limit || '∞'}
                                        </span>
                                    </div>

                                    <button
                                        onClick={(e) => { e.stopPropagation(); handleDelete(acc.id); }}
                                        className="absolute top-3 right-3 text-red-500/50 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Right Side: Form */}
                <div className="w-1/2 p-6 bg-black/40 overflow-y-auto">
                    {showForm ? (
                        <div className="space-y-5 animate-fadeIn">
                            <h3 className="text-white font-medium border-b border-gold9/20 pb-2 mb-4">
                                {isAdding ? 'Add Account' : 'Edit Account'}
                            </h3>

                            {error && (
                                <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-3 rounded text-sm break-words">
                                    {error}
                                </div>
                            )}

                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Account Name</label>
                                <input
                                    type="text"
                                    name="name"
                                    value={formData.name}
                                    onChange={handleChange}
                                    placeholder="e.g. Production Key 1"
                                    className="w-full bg-gray-900 border border-gray-700 focus:border-gold9/50 rounded px-3 py-2 text-white outline-none transition-colors"
                                />
                            </div>

                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Jules API Key *</label>
                                <div className="relative">
                                    <Key className="absolute left-3 top-2.5 text-gray-500" size={14} />
                                    <input
                                        type="password"
                                        name="api_key"
                                        value={formData.api_key}
                                        onChange={handleChange}
                                        placeholder="x-goog-api-key"
                                        className="w-full bg-gray-900 border border-gray-700 focus:border-gold9/50 rounded pl-9 pr-3 py-2 text-white outline-none transition-colors font-mono text-sm"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs text-gray-400 mb-1" title="Leave blank for infinite">Concurrent Limit</label>
                                    <input
                                        type="number"
                                        name="concurrent_sessions_limit"
                                        value={formData.concurrent_sessions_limit}
                                        onChange={handleChange}
                                        placeholder="∞"
                                        min="1"
                                        className="w-full bg-gray-900 border border-gray-700 focus:border-gold9/50 rounded px-3 py-2 text-white outline-none transition-colors"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-gray-400 mb-1" title="Leave blank for infinite">Total Limit</label>
                                    <input
                                        type="number"
                                        name="total_sessions_limit"
                                        value={formData.total_sessions_limit}
                                        onChange={handleChange}
                                        placeholder="∞"
                                        min="1"
                                        className="w-full bg-gray-900 border border-gray-700 focus:border-gold9/50 rounded px-3 py-2 text-white outline-none transition-colors"
                                    />
                                </div>
                            </div>

                            <div className="flex gap-3 pt-4 border-t border-gray-800">
                                <button
                                    onClick={handleSave}
                                    disabled={!formData.api_key}
                                    className="flex-1 flex items-center justify-center gap-2 bg-gold9 text-black font-semibold py-2 rounded hover:bg-gold8 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <Save size={16} /> Save
                                </button>
                                <button
                                    onClick={handleCancel}
                                    className="px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-700 transition-colors"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-gray-500">
                            <Server size={48} className="opacity-20 mb-4" />
                            <p>Select an account to edit or add a new one.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default FleetSettingsWindow;
