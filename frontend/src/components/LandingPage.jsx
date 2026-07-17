import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Cat, UserRound, ArrowUp, ArrowRight, MessageSquare, BarChart3, Stethoscope, RefreshCcw, Database, FlaskConical, Building, Cloud } from 'lucide-react';
import './LandingPage.css';
import pusheenCat from '../assets/pusheen.png';
import pusheenDoc from '../assets/pusheen-doc.png';
import openaiIcon from '../assets/openai.svg';
import geminiIcon from '../assets/gemini.svg';
import anthropicIcon from '../assets/anthropic.svg';
import ollamaIcon from '../assets/ollama.svg';

const interactions = [
    {
        query: "Who were the top 2 most frequent patients last month?",
        response: (
            <div className="animate-slide-up-fade">
                <p className="mb-3 text-sm">Based on the records from last month, here are the top 2 most frequent visitors:</p>
                
                {/* Inline Table Mockup */}
                <div className="mt-4 border border-outline-variant rounded-lg bg-surface overflow-hidden">
                    <div className="flex items-center justify-between p-3 border-b border-outline-variant bg-surface-container-lowest">
                        <div className="flex items-center gap-2">
                            <BarChart3 size={14} className="text-primary" />
                            <span className="font-display text-sm font-semibold text-on-surface">Frequent Visitors</span>
                        </div>
                    </div>
                    <div className="p-0">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-surface-container-low text-xs uppercase tracking-wider text-on-surface-variant font-display font-medium border-b border-outline-variant">
                                <tr>
                                    <th className="px-4 py-2">Patient</th>
                                    <th className="px-4 py-2">Owner</th>
                                    <th className="px-4 py-2 text-right">Visits</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr className="border-b border-outline-variant/50">
                                    <td className="px-4 py-2 text-on-surface font-medium">Bella (Golden Retriever)</td>
                                    <td className="px-4 py-2 text-on-surface-variant">Sarah J.</td>
                                    <td className="px-4 py-2 text-primary text-right font-medium">4</td>
                                </tr>
                                <tr>
                                    <td className="px-4 py-2 text-on-surface font-medium">Max (Tabby Cat)</td>
                                    <td className="px-4 py-2 text-on-surface-variant">David L.</td>
                                    <td className="px-4 py-2 text-on-surface-variant text-right">3</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        )
    },
    {
        query: "Did Charlie (the Beagle) have any reactions to his last vaccine?",
        response: (
            <div className="animate-slide-up-fade">
                <p className="mb-3 text-sm">I checked Charlie's records. Yes, he had a mild reaction last year:</p>
                <div className="p-4 border border-red-500/30 bg-red-500/5 rounded-lg text-sm text-red-200">
                    <div className="flex items-center gap-2 mb-2 text-red-400">
                        <Stethoscope size={16} />
                        <strong className="font-semibold">Clinical Note - Oct 12, 2025</strong>
                    </div>
                    Patient presented with mild facial swelling and lethargy 4 hours post DHPP administration. Administered 1mg/kg Diphenhydramine. Owner advised to monitor.
                </div>
            </div>
        )
    },
    {
        query: "Generate a summary of today's appointments.",
        response: (
            <div className="animate-slide-up-fade">
                <p className="mb-3 text-sm">Here is the summary for today (14 total appointments):</p>
                <ul className="space-y-3 text-sm text-on-surface-variant">
                    <li className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_rgba(182,106,255,0.6)]"></div> 
                        <span><strong className="text-on-surface">8 Wellness Exams</strong> (4 canine, 4 feline)</span>
                    </li>
                    <li className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]"></div> 
                        <span><strong className="text-on-surface">3 Vaccinations</strong> (Routine)</span>
                    </li>
                    <li className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.6)]"></div> 
                        <span><strong className="text-on-surface">2 Urgent Care</strong> (GI upset, Laceration)</span>
                    </li>
                    <li className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.6)]"></div> 
                        <span><strong className="text-on-surface">1 Dental Cleaning</strong></span>
                    </li>
                </ul>
            </div>
        )
    }
];

const HeroChatMockup = () => {
    const [step, setStep] = useState(0);
    const [inputText, setInputText] = useState("");
    const [interactionIndex, setInteractionIndex] = useState(0);

    const currentInteraction = interactions[interactionIndex];

    useEffect(() => {
        if (step === 0) {
            let i = 0;
            const targetText = currentInteraction.query;
            const interval = setInterval(() => {
                setInputText(targetText.slice(0, i + 1));
                i++;
                if (i >= targetText.length) {
                    clearInterval(interval);
                    setTimeout(() => setStep(1), 600);
                }
            }, 35);
            return () => clearInterval(interval);
        } else if (step === 1) {
            const t = setTimeout(() => setStep(2), 500);
            return () => clearTimeout(t);
        } else if (step === 2) {
            const t = setTimeout(() => setStep(3), 1500);
            return () => clearTimeout(t);
        } else if (step === 3) {
            const t = setTimeout(() => {
                setStep(0);
                setInputText("");
                setInteractionIndex((prev) => (prev + 1) % interactions.length);
            }, 7000);
            return () => clearTimeout(t);
        }
    }, [step, currentInteraction.query]);

    return (
        <div className="bg-surface-container-lowest border border-outline-variant shadow-2xl rounded-xl overflow-hidden relative z-10 flex flex-col h-[550px] rotate-y-neg2 rotate-x-1 transition-transform hover:rotate-0 duration-500">
            {/* Topbar */}
            <div className="h-[56px] px-6 border-b border-outline-variant/50 flex items-center justify-between shrink-0" style={{ background: 'linear-gradient(180deg, var(--color-surface) 0%, color-mix(in oklch, var(--color-surface) 60%, var(--color-paper)) 100%)' }}>
                <div className="flex items-center gap-2">
                    <Cat size={20} className="text-primary" strokeWidth={2.25} />
                    <span className="font-display font-semibold text-on-surface tracking-tight">Vetlog AI</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-on-surface-variant bg-surface-container-low border border-outline-variant rounded-md px-3 py-1">
                    <span>245 tokens</span>
                </div>
            </div>
            
            {/* Chat Window */}
            <div className="flex-1 bg-surface-container-lowest p-6 overflow-y-auto flex flex-col gap-8">
                {/* User Message */}
                {step >= 1 && (
                    <div className="flex items-start gap-3 flex-row-reverse animate-slide-up-fade">
                        <div className="w-[22px] h-[22px] rounded-full bg-surface-container-low border border-outline-variant text-on-surface-variant flex items-center justify-center shrink-0 mt-[2px]">
                            <UserRound size={12} strokeWidth={2.5} />
                        </div>
                        <div className="bg-surface-container border border-outline-variant rounded-[24px] rounded-tr-md px-4 py-3 text-on-surface text-base max-w-[75%] leading-[1.65]">
                            {currentInteraction.query}
                        </div>
                    </div>
                )}

                {/* AI Message */}
                {step >= 2 && (
                    <div className="flex items-start gap-3 animate-slide-up-fade">
                        <div className="w-[22px] h-[22px] rounded-full bg-primary/10 border border-primary/20 text-primary flex items-center justify-center shrink-0 mt-[2px]">
                            <Cat size={14} strokeWidth={2.25} />
                        </div>
                        <div className="text-on-surface text-base leading-[1.75] w-full">
                            {step === 2 ? (
                                <div className="flex items-center gap-1.5 h-6 px-1">
                                    <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce"></span>
                                    <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                    <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                                </div>
                            ) : (
                                currentInteraction.response
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Input Bar */}
            <div className="p-4 pt-0 shrink-0" style={{ background: 'linear-gradient(180deg, transparent 0%, var(--color-paper) 40%)' }}>
                <div className="bg-surface border border-outline-variant rounded-2xl p-3 pl-5 shadow-md flex items-end gap-3 transition-shadow hover:shadow-lg">
                    <div className={`flex-1 text-sm py-1 ${step === 0 && inputText ? 'text-on-surface' : 'text-on-surface-variant/60'}`}>
                        {step === 0 ? (
                            <span>{inputText}<span className="animate-pulse inline-block w-[2px] h-[1em] bg-primary ml-[1px] align-middle -mt-[2px]"></span></span>
                        ) : (
                            "Ask about your patients, treatments, or clinic activity…"
                        )}
                    </div>
                    <div className="w-[32px] h-[32px] rounded-lg bg-primary text-on-primary flex items-center justify-center shrink-0 shadow-sm cursor-pointer hover:opacity-90 transition-opacity">
                        <ArrowUp size={16} strokeWidth={2.5} />
                    </div>
                </div>
                <p className="text-center text-xs text-on-surface-variant/50 mt-3 font-medium">
                    Enter to send <span className="opacity-50 mx-1">·</span> Shift + Enter for new line
                </p>
            </div>
        </div>
    );
};

export default function LandingPage() {
    useEffect(() => {
        const handleScroll = () => {
            const nav = document.getElementById('main-nav');
            if (nav) {
                if (window.scrollY > 20) {
                    nav.classList.add('shadow-md');
                    nav.classList.replace('bg-surface-container/80', 'bg-surface-container');
                } else {
                    nav.classList.remove('shadow-md');
                    nav.classList.replace('bg-surface-container', 'bg-surface-container/80');
                }
            }
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <div className="bg-surface text-on-surface font-body-md antialiased overflow-x-hidden relative selection:bg-primary/30 selection:text-primary-100 paper-grain min-h-screen flex flex-col">
            {/* Hallmark · genre: modern-minimal · macrostructure: Mockup split browser framed · theme: Vet Violet */}

            {/* Floating Pill Nav */}
            <nav className="fixed top-6 left-0 right-0 mx-auto z-50 w-[90%] max-w-5xl bg-surface-container/80 backdrop-blur-md border border-outline-variant/30 rounded-full px-6 py-3 flex items-center justify-between shadow-lg" id="main-nav">
                <div className="flex items-center gap-sm">
                    <Cat className="text-primary w-6 h-6" strokeWidth={2.25} />
                    <span className="font-headline-md text-body-lg font-bold text-primary">Vetlog-AI</span>
                </div>
                <div className="hidden md:flex items-center gap-lg">
                    <a className="font-label-md text-label-md text-on-surface-variant hover:text-primary transition-colors px-sm py-xs no-underline" href="#features">Features</a>
                    <a className="font-label-md text-label-md text-on-surface-variant hover:text-primary transition-colors px-sm py-xs no-underline" href="#integrations">Integrations</a>
                </div>
                <div className="flex items-center">
                    <Link to="/app" className="font-label-md text-label-md bg-primary text-on-primary px-4 py-2 rounded-full hover:-translate-y-[1px] active:scale-[0.98] transition-all duration-200 whitespace-nowrap no-underline">
                        Login / Sign up
                    </Link>
                </div>
            </nav>

            {/* Hero Section (6/6 Split) */}
            <main className="pt-[160px] pb-32 min-h-screen flex flex-col justify-center relative z-10">
                <div className="max-w-7xl mx-auto px-6 md:px-10 w-full grid grid-cols-1 lg:grid-cols-12 gap-16 items-center relative">
                    
                    {/* Text Content */}
                    <div className="lg:col-span-6 flex flex-col items-start text-left">
                        <h1 className="font-display-lg text-5xl md:text-[56px] leading-[1.1] text-on-surface tracking-tight mb-6">
                            Unlock the intelligence in your clinic's <span className="text-primary italic font-serif">conversations.</span>
                        </h1>
                        <p className="font-body-lg text-xl text-on-surface-variant max-w-xl mb-10">
                            Vetlog-AI turns your clinic's WhatsApp history into actionable insights. Query your data using natural language and get answers in seconds.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
                            <Link to="/app" className="font-label-md text-label-md bg-primary text-on-primary px-8 py-3.5 rounded-lg hover:-translate-y-[1px] active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 whitespace-nowrap no-underline">
                                Get Started
                                <ArrowRight size={18} />
                            </Link>
                        </div>
                    </div>
                    
                    {/* UI Mockup Presentation */}
                    <div className="lg:col-span-6 relative perspective-1000">
                        <HeroChatMockup />
                        
                        {/* Decorative background glow behind the mockup */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-primary/20 blur-[100px] rounded-full z-0 pointer-events-none"></div>
                    </div>
                </div>
            </main>

            {/* Features Showcase Section (Asymmetric Bento Grid) */}
            <section id="features" className="relative py-24 border-t border-outline-variant/30">
                <div className="max-w-7xl mx-auto px-6 md:px-10 relative z-10">
                    <div className="mb-16 md:w-2/3">
                        <h2 className="font-headline-lg text-3xl font-bold text-on-surface mb-4 tracking-tight">
                            Built for modern veterinary care.
                        </h2>
                        <p className="font-body-lg text-lg text-on-surface-variant">
                            Intelligent tools engineered specifically for the high-stress, fast-paced environment of your clinic.
                        </p>
                    </div>
                    {/* Asymmetric Grid */}
                    <div className="bento">
                        {/* Card 1: Wide primary feature (2x1) */}
                        <div className="bento-cell span-2x1 bg-surface-container border border-outline-variant/30 rounded-2xl p-8 flex flex-col justify-between hover:bg-surface-container-low transition-colors duration-300">
                            <div>
                                <div className="flex items-center gap-3 mb-4">
                                    <MessageSquare className="text-primary w-6 h-6" />
                                    <h3 className="font-headline-md text-xl font-semibold tracking-tight">Natural Language Queries</h3>
                                </div>
                                <p className="font-body-md text-on-surface-variant mb-6">
                                    Talk to your data like you talk to a colleague. Retrieve patient histories, lab results, and treatment plans using intuitive, conversational prompts.
                                </p>
                            </div>
                            <div className="flex items-center gap-2 text-primary group cursor-pointer w-fit">
                                <span className="font-label-md font-medium">Explore queries</span>
                                <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                            </div>
                        </div>

                        {/* Card 2: WhatsApp Sync (1x1) */}
                        <div className="bento-cell span-1x1 bg-surface-container border border-outline-variant/30 rounded-2xl p-8 flex flex-col hover:bg-surface-container-low transition-colors duration-300 relative overflow-hidden group">
                            <h3 className="font-headline-md text-xl font-semibold mb-3 tracking-tight z-10 relative">WhatsApp Sync</h3>
                            <p className="font-body-md text-on-surface-variant text-sm z-10 relative">
                                Automatically capture client communications directly into the patient record.
                            </p>
                            <img 
                                src={pusheenCat} 
                                alt="Pusheen holding WhatsApp" 
                                className="absolute bottom-[-10px] right-[-10px] w-48 h-auto object-contain z-0 pointer-events-none group-hover:scale-[1.03] transition-transform duration-500 origin-bottom-right"
                            />
                        </div>

                        {/* Card 3: Clinical Context (1x1) */}
                        <div className="bento-cell span-1x1 bg-surface-container border border-outline-variant/30 rounded-2xl p-8 flex flex-col hover:bg-surface-container-low transition-colors duration-300 relative overflow-hidden group">
                            <h3 className="font-headline-md text-xl font-semibold mb-3 tracking-tight z-10 relative">Clinical Context</h3>
                            <p className="font-body-md text-on-surface-variant text-sm z-10 relative">
                                Context-aware AI that understands veterinary terminology.
                            </p>
                            <img 
                                src={pusheenDoc} 
                                alt="Dr. Pusheen" 
                                className="absolute bottom-[-10px] right-[-10px] w-48 h-auto object-contain z-0 pointer-events-none group-hover:scale-[1.03] transition-transform duration-500 origin-bottom-right"
                            />
                        </div>
                        
                        {/* Card 4: Real-Time Analytics (4x1) */}
                        <div className="bento-cell span-4x1 bg-surface-container border border-outline-variant/30 rounded-2xl p-8 flex flex-col md:flex-row items-center justify-between gap-8 hover:bg-surface-container-low transition-colors duration-300 overflow-hidden">
                            <div className="md:w-1/2">
                                <div className="flex items-center gap-3 mb-4">
                                    <BarChart3 className="text-primary w-6 h-6" />
                                    <h3 className="font-headline-md text-xl font-semibold tracking-tight">Real-Time Analytics</h3>
                                </div>
                                <p className="font-body-md text-on-surface-variant">
                                    Instant visibility into patient trends and clinic performance. Monitor appointment volume and common diagnoses with automated dashboards that update as you work.
                                </p>
                            </div>
                            <div className="md:w-1/2 w-full h-32 relative mt-6 md:mt-0">
                                <svg viewBox="0 0 400 100" className="w-full h-full overflow-visible" preserveAspectRatio="none">
                                    <defs>
                                        <linearGradient id="chart-gradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="oklch(62% 0.20 295)" stopOpacity="0.4" />
                                            <stop offset="100%" stopColor="oklch(62% 0.20 295)" stopOpacity="0.0" />
                                        </linearGradient>
                                        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                                            <feGaussianBlur stdDeviation="3" result="blur" />
                                            <feComposite in="SourceGraphic" in2="blur" operator="over" />
                                        </filter>
                                    </defs>
                                    
                                    {/* Filled area */}
                                    <path 
                                        d="M 0,100 L 0,80 C 50,80 80,50 120,60 C 160,70 200,20 240,30 C 280,40 320,15 400,20 L 400,100 Z" 
                                        fill="url(#chart-gradient)" 
                                    />
                                    
                                    {/* Line */}
                                    <path 
                                        d="M 0,80 C 50,80 80,50 120,60 C 160,70 200,20 240,30 C 280,40 320,15 400,20" 
                                        fill="none" 
                                        stroke="oklch(62% 0.20 295)" 
                                        strokeWidth="3" 
                                        strokeLinecap="round"
                                    />
                                    
                                    {/* Data points */}
                                    <circle cx="120" cy="60" r="4" fill="oklch(11% 0.006 280)" stroke="oklch(62% 0.20 295)" strokeWidth="2" />
                                    <circle cx="240" cy="30" r="4" fill="oklch(11% 0.006 280)" stroke="oklch(62% 0.20 295)" strokeWidth="2" />
                                    <circle cx="400" cy="20" r="5" fill="oklch(62% 0.20 295)" />
                                </svg>
                                
                                {/* Floating tooltip mockup */}
                                <div className="absolute right-0 top-0 -translate-y-2 translate-x-2 bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-1.5 shadow-lg flex flex-col items-end">
                                    <span className="text-[10px] uppercase tracking-wider text-on-surface-variant font-display font-medium">This Week</span>
                                    <span className="text-sm font-display font-semibold text-primary">+24% Visits</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Integrations Section */}
            <section className="py-24 border-t border-outline-variant/30">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="text-center mb-12">
                        <p className="font-label-md text-primary uppercase tracking-wider mb-3">Model Agnostic</p>
                        <h2 className="font-display-lg text-3xl font-bold tracking-tight">Works with any A.I. model/provider.</h2>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="flex flex-col items-center justify-center p-8 bg-surface-container rounded-2xl border border-outline-variant/30 hover:bg-surface-container-low transition-colors duration-300">
                            <img src={openaiIcon} alt="ChatGPT" className="w-8 h-8 mb-4" />
                            <span className="font-label-md font-semibold">ChatGPT</span>
                        </div>
                        <div className="flex flex-col items-center justify-center p-8 bg-surface-container rounded-2xl border border-outline-variant/30 hover:bg-surface-container-low transition-colors duration-300">
                            <img src={geminiIcon} alt="Gemini" className="w-8 h-8 mb-4" />
                            <span className="font-label-md font-semibold">Gemini</span>
                        </div>
                        <div className="flex flex-col items-center justify-center p-8 bg-surface-container rounded-2xl border border-outline-variant/30 hover:bg-surface-container-low transition-colors duration-300">
                            <img src={anthropicIcon} alt="Claude" className="w-8 h-8 mb-4" />
                            <span className="font-label-md font-semibold">Claude</span>
                        </div>
                        <div className="flex flex-col items-center justify-center p-8 bg-surface-container rounded-2xl border border-outline-variant/30 hover:bg-surface-container-low transition-colors duration-300">
                            <img src={ollamaIcon} alt="Ollama" className="w-8 h-8 mb-4" />
                            <span className="font-label-md font-semibold">Ollama</span>
                        </div>
                    </div>
                </div>
            </section>


            {/* Footer (Ft2 Inline single line) */}
            <footer className="border-t border-outline-variant/50 py-10 px-6 md:px-10 w-full text-sm text-on-surface-variant flex flex-col md:flex-row items-center justify-between gap-4 bg-surface-container-lowest">
                <div>© 2026 Vetlog-AI Inc.</div>
                <div className="flex items-center gap-6 text-sm text-on-surface-variant">
                    <a href="#" className="hover:text-primary transition-colors no-underline">Privacy</a>
                    <a href="#" className="hover:text-primary transition-colors no-underline">Terms</a>
                    <a href="#" className="hover:text-primary transition-colors no-underline">Twitter</a>
                    <a href="#" className="hover:text-primary transition-colors no-underline">LinkedIn</a>
                </div>
            </footer>
        </div>
    );
}
