import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Activity,
    Wifi,
    Cpu,
    Layers,
    CheckSquare,
    Printer,
    Zap,
    Clock,
    Globe,
    Shield,
    AlertCircle
} from 'lucide-react';

const WarRoomDashboard = ({ data, onClose }) => {
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    // Destructure data with defaults
    const {
        project = "UNKNOWN",
        trello = [],
        jules = [],
        devices = [],
        printers = [],
        git = { branch: 'unknown', branches: [], status: '' },
        system_status = "ONLINE"
    } = data || {};

    const containerVariants = {
        hidden: { opacity: 0, scale: 0.95 },
        visible: {
            opacity: 1,
            scale: 1,
            transition: { duration: 0.5, staggerChildren: 0.1 }
        },
        exit: { opacity: 0, scale: 0.95 }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
    };

    return (
        <AnimatePresence>
            <motion.div
                className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-xl flex flex-col p-6 text-gold9 font-mono overflow-hidden"
                initial="hidden"
                animate="visible"
                exit="exit"
                variants={containerVariants}
            >
                {/* BACKGROUND HUD ELEMENTS */}
                <div className="absolute inset-0 pointer-events-none">
                    <div className="absolute top-0 left-0 w-64 h-64 border-l-2 border-t-2 border-gold9/30 rounded-tl-3xl"></div>
                    <div className="absolute top-0 right-0 w-64 h-64 border-r-2 border-t-2 border-gold9/30 rounded-tr-3xl"></div>
                    <div className="absolute bottom-0 left-0 w-64 h-64 border-l-2 border-b-2 border-gold9/30 rounded-bl-3xl"></div>
                    <div className="absolute bottom-0 right-0 w-64 h-64 border-r-2 border-b-2 border-gold9/30 rounded-br-3xl"></div>
                    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 mix-blend-overlay"></div>
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] border border-gold9/5 rounded-full"></div>
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] border border-dashed border-gold9/10 rounded-full animate-spin-slow"></div>
                </div>

                {/* HEADER */}
                <motion.header variants={itemVariants} className="relative z-10 flex justify-between items-center mb-6 border-b border-gold9/20 pb-4">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-gold9/10 border border-gold9 rounded-lg flex items-center justify-center">
                            <Shield className="w-6 h-6 text-gold9" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold tracking-[0.2em] text-gold9 drop-shadow-[0_0_10px_rgba(255,215,0,0.5)]">
                                WAR ROOM
                            </h1>
                            <div className="flex items-center gap-2 text-xs text-gold9/60 tracking-widest">
                                <span>OPERATION: {project.toUpperCase()}</span>
                                <span className="w-1 h-1 bg-gold9 rounded-full"></span>
                                <span className={system_status === "ONLINE" ? "text-green-500" : "text-red-500"}>
                                    SYSTEM {system_status}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-6">
                        <div className="text-right">
                            <div className="text-2xl font-bold tracking-widest">
                                {time.toLocaleTimeString([], { hour12: false })}
                            </div>
                            <div className="text-xs text-gold9/60 tracking-[0.2em]">
                                {time.toLocaleDateString().toUpperCase()}
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="px-4 py-2 border border-gold9/30 hover:bg-gold9/10 hover:border-gold9 rounded text-xs tracking-widest transition-all"
                        >
                            CLOSE HUD
                        </button>
                    </div>
                </motion.header>

                {/* MAIN GRID */}
                <div className="relative z-10 grid grid-cols-12 grid-rows-6 gap-6 flex-1 min-h-0">

                    {/* COL 1: INTEL (TRELLO) - Spans 4 cols, full height */}
                    <motion.div
                        variants={itemVariants}
                        className="col-span-4 row-span-6 bg-black/40 border border-gold9/20 rounded-xl p-4 flex flex-col relative overflow-hidden group hover:border-gold9/40 transition-colors"
                    >
                        <div className="absolute top-0 right-0 p-2 opacity-50">
                            <Layers className="w-24 h-24 text-gold9/5" />
                        </div>
                        <h2 className="flex items-center gap-2 text-lg font-bold tracking-widest border-b border-gold9/10 pb-2 mb-4">
                            <CheckSquare className="w-5 h-5 text-gold9" />
                            ACTIVE OBJECTIVES
                        </h2>
                        <div className="flex-1 overflow-y-auto scrollbar-hide space-y-3">
                            {trello.length === 0 ? (
                                <div className="text-center text-gold9/40 py-10 italic">No active objectives detected.</div>
                            ) : (
                                trello.map((card, i) => (
                                    <div key={i} className="bg-gold9/5 border border-gold9/10 p-3 rounded hover:bg-gold9/10 transition-colors">
                                        <div className="text-xs text-gold9/50 mb-1 flex justify-between">
                                            <span>{card.listName || 'PENDING'}</span>
                                            <span>#{card.idShort}</span>
                                        </div>
                                        <div className="font-medium text-sm text-gray-200">{card.name}</div>
                                    </div>
                                ))
                            )}
                        </div>
                    </motion.div>

                    {/* COL 2: CENTER COMMS (JULES) - Spans 5 cols, Top 4 rows */}
                    <motion.div
                        variants={itemVariants}
                        className="col-span-5 row-span-4 bg-black/40 border border-gold9/20 rounded-xl p-4 flex flex-col relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 p-2 opacity-50">
                            <Activity className="w-24 h-24 text-gold9/5" />
                        </div>
                        <h2 className="flex items-center gap-2 text-lg font-bold tracking-widest border-b border-gold9/10 pb-2 mb-4">
                            <Cpu className="w-5 h-5 text-gold9" />
                            AGENT STATUS (JULES)
                        </h2>
                        <div className="flex-1 overflow-y-auto scrollbar-hide">
                             {jules.length === 0 ? (
                                <div className="h-full flex flex-col items-center justify-center text-gold9/40 gap-2">
                                    <Activity className="w-8 h-8 opacity-50" />
                                    <span className="italic">No active agents in field.</span>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 gap-3">
                                    {jules.map((session, i) => (
                                        <div key={i} className="flex items-center gap-3 bg-gold9/5 border border-gold9/10 p-3 rounded">
                                            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                                            <div className="flex-1">
                                                <div className="text-sm font-bold text-gold9">{session.title || session.id}</div>
                                                <div className="text-xs text-gold9/60">STATE: {session.state || 'UNKNOWN'}</div>
                                            </div>
                                            <div className="text-xs font-mono text-gold9/40">
                                                ID: {session.id.substring(0,6)}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </motion.div>

                    {/* COL 2 BOTTOM: QUICK STATS - Spans 5 cols, Bottom 2 rows */}
                    <motion.div
                        variants={itemVariants}
                        className="col-span-5 row-span-2 grid grid-cols-3 gap-4"
                    >
                        <div className="bg-black/40 border border-gold9/20 rounded-xl p-3 flex flex-col justify-between">
                            <div className="text-xs text-gold9/60">LATENCY</div>
                            <div className="text-2xl font-bold text-green-400">24ms</div>
                            <Activity className="w-4 h-4 self-end text-gold9/30" />
                        </div>
                        <div className="bg-black/40 border border-gold9/20 rounded-xl p-3 flex flex-col justify-between">
                            <div className="text-xs text-gold9/60">CPU LOAD</div>
                            <div className="text-2xl font-bold text-gold9">12%</div>
                            <Cpu className="w-4 h-4 self-end text-gold9/30" />
                        </div>
                        <div className="bg-black/40 border border-gold9/20 rounded-xl p-3 flex flex-col justify-between">
                            <div className="text-xs text-gold9/60">NETWORK</div>
                            <div className="text-2xl font-bold text-blue-400">1Gbps</div>
                            <Globe className="w-4 h-4 self-end text-gold9/30" />
                        </div>
                    </motion.div>

                    {/* COL 3: HARDWARE (DEVICES/PRINTERS/GIT) - Spans 3 cols, full height */}
                    <motion.div
                        variants={itemVariants}
                        className="col-span-3 row-span-6 flex flex-col gap-4"
                    >
                        {/* GIT OPS */}
                        <div className="bg-black/40 border border-gold9/20 rounded-xl p-4 relative overflow-hidden">
                             <h2 className="flex items-center gap-2 text-sm font-bold tracking-widest border-b border-gold9/10 pb-2 mb-2">
                                <span className="text-gold9">GIT OPS</span>
                            </h2>
                            <div className="text-xs space-y-2">
                                <div className="flex justify-between">
                                    <span className="text-gold9/60">BRANCH</span>
                                    <span className="font-bold text-green-400">{git.branch}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gold9/60">STATUS</span>
                                    <span className="font-mono text-[10px]">{git.status ? 'MODIFIED' : 'CLEAN'}</span>
                                </div>
                            </div>
                        </div>

                        {/* PRINTERS */}
                        <div className="flex-1 bg-black/40 border border-gold9/20 rounded-xl p-4 relative overflow-hidden">
                             <h2 className="flex items-center gap-2 text-sm font-bold tracking-widest border-b border-gold9/10 pb-2 mb-4">
                                <Printer className="w-4 h-4 text-gold9" />
                                FABRICATION
                            </h2>
                            <div className="space-y-3">
                                {printers.length === 0 ? (
                                    <div className="text-xs text-gold9/40 italic">No units online.</div>
                                ) : (
                                    printers.map((p, i) => (
                                        <div key={i} className="bg-gold9/5 p-2 rounded border border-gold9/10">
                                            <div className="flex justify-between items-center mb-1">
                                                <span className="text-xs font-bold">{p.name}</span>
                                                <div className={`w-1.5 h-1.5 rounded-full ${p.state === 'printing' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`}></div>
                                            </div>
                                            <div className="text-[10px] text-gold9/60 flex justify-between">
                                                <span>{p.state || 'IDLE'}</span>
                                                <span>{p.temp ? `${p.temp}°C` : '--'}</span>
                                            </div>
                                            {p.progress > 0 && (
                                                <div className="w-full h-1 bg-gray-800 rounded-full mt-2 overflow-hidden">
                                                    <div className="h-full bg-gold9" style={{ width: `${p.progress}%` }}></div>
                                                </div>
                                            )}
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* DEVICES */}
                        <div className="flex-1 bg-black/40 border border-gold9/20 rounded-xl p-4 relative overflow-hidden">
                            <h2 className="flex items-center gap-2 text-sm font-bold tracking-widest border-b border-gold9/10 pb-2 mb-4">
                                <Zap className="w-4 h-4 text-gold9" />
                                FIELD ASSETS
                            </h2>
                            <div className="space-y-2 max-h-[200px] overflow-y-auto scrollbar-hide">
                                 {devices.length === 0 ? (
                                    <div className="text-xs text-gold9/40 italic">No assets detected.</div>
                                ) : (
                                    devices.map((d, i) => (
                                        <div key={i} className="flex items-center justify-between bg-gold9/5 p-2 rounded border border-gold9/10">
                                            <span className="text-xs truncate max-w-[100px]">{d.alias}</span>
                                            <div className={`px-2 py-0.5 rounded text-[10px] font-bold ${d.is_on ? 'bg-gold9 text-black' : 'bg-gray-800 text-gray-500'}`}>
                                                {d.is_on ? 'ON' : 'OFF'}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </motion.div>

                </div>

                {/* FOOTER */}
                <motion.div variants={itemVariants} className="mt-4 text-[10px] text-gold9/40 flex justify-between uppercase tracking-widest">
                    <div>SECURE CONNECTION ESTABLISHED</div>
                    <div>A.D.A OS v2.0 // AUTH: JAMES</div>
                </motion.div>

            </motion.div>
        </AnimatePresence>
    );
};

export default WarRoomDashboard;
