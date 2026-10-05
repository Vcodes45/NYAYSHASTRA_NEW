import { useUser } from '@clerk/clerk-react';
import { motion } from 'framer-motion';
import { Search, Plus, MessageSquare, History, Clock, BookOpen, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { useEffect, useState } from 'react';
import { warmUpDatabase, getDashboardStats } from '@/services/api';
import { useChatHistory } from '@/hooks/useApi';
import { Experience3D } from './3d/core/Experience3D';
import { SketchfabScrollExperience } from './3d/core/SketchfabScrollExperience';
import { MODEL_REGISTRY } from './3d/config/ModelRegistry';
interface AuthenticatedDashboardProps {
  language: 'en' | 'hi';
  onStartChat: (message?: string) => void;
  onLoadSession?: (sessionId: string) => void;
}

interface DashboardStats {
  savedStatutes: number;
  casesAnalyzed: number;
  activeSessions: number;
}

export const AuthenticatedDashboard = ({ language, onStartChat, onLoadSession }: AuthenticatedDashboardProps) => {
  const { user } = useUser();
  const { sessions: recentChats, loading: historyLoading } = useChatHistory();
  const [stats, setStats] = useState<DashboardStats>({
    savedStatutes: 0,
    casesAnalyzed: 0,
    activeSessions: 0
  });
  const [statsLoading, setStatsLoading] = useState(true);

  // Warm up database and fetch stats on component mount
  useEffect(() => {
    warmUpDatabase();
    fetchStats();
  }, []);

  // Update active sessions count when chat history changes
  useEffect(() => {
    setStats(prev => ({
      ...prev,
      activeSessions: recentChats.length
    }));
  }, [recentChats]);

  const fetchStats = async () => {
    setStatsLoading(true);
    try {
      const data = await getDashboardStats();
      setStats(data);
    } catch (error) {
      console.log('Stats fetch error (backend may be starting):', error);
    } finally {
      setStatsLoading(false);
    }
  };

  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.6,
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, scale: 0.95 },
    visible: { opacity: 1, scale: 1 }
  };

  // Get display chats (limit to 6 for the dashboard)
  const displayChats = recentChats.slice(0, 6);

  return (
    <div className="flex-1 overflow-y-auto bg-[#faf7f2] dark:bg-[#0f1115] relative">
      {/* 3D Lady Justice Hero Background */}
      <div className="absolute right-0 top-0 w-full md:w-1/2 h-[600px] pointer-events-none opacity-40 md:opacity-100 z-0">
        <Experience3D config={MODEL_REGISTRY.ladyJustice} className="w-full h-full pointer-events-auto" />
      </div>

      <div className="container mx-auto px-4 py-12 max-w-6xl relative z-10">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-2"
          >
            <h2 className="text-xl md:text-4xl font-serif font-medium text-muted-foreground tracking-wide">
              {language === 'en' ? 'Hello,' : 'नमस्ते,'}
            </h2>
            <h3 className="text-6xl md:text-6xl font-serif font-black text-primary tracking-tighter -mt-2">
              {user?.firstName || (language === 'en' ? 'Advocate' : 'अधिवक्ता')}
            </h3>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <Button
              onClick={() => onStartChat()}
              size="lg"
              className="rounded-2xl h-14 px-8 text-lg font-bold shadow-xl hover:shadow-primary/20 transition-all gap-3 bg-primary text-primary-foreground group"
            >
              <Plus className="h-6 w-6 group-hover:rotate-90 transition-transform duration-300" />
              <span>{language === 'en' ? 'New Chat' : 'नई चैट'}</span>
            </Button>
          </motion.div>
        </div>

        {/* Main Search & History Area */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="space-y-10"
        >
          {/* Search Wrapper */}
          <div className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-primary/20 to-accent/20 rounded-[2.5rem] blur opacity-25 group-hover:opacity-50 transition duration-1000"></div>
            <div className="relative glass-strong rounded-[2rem] p-8 shadow-2xl border border-white/20 dark:border-white/5">
              <div className="relative">
                <Search className="absolute left-6 top-1/2 -translate-y-1/2 h-6 w-6 text-primary/60" />
                <Input
                  className="w-full bg-background/50 border-2 border-primary/10 hover:border-primary/30 focus:border-primary rounded-2xl h-16 pl-16 pr-6 text-xl shadow-inner transition-all"
                  placeholder={language === 'en' ? "Search for laws, cases, or chat history..." : "कानून, मामले या चैट इतिहास खोजें..."}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                      onStartChat(e.currentTarget.value.trim());
                    }
                  }}
                />
              </div>

              {/* Chat History Header */}
              <div className="flex items-center justify-between mt-12 mb-6">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-6 bg-primary rounded-full" />
                  <h4 className="text-xl font-serif font-bold text-foreground">
                    {language === 'en' ? 'Recent Conversations' : 'हाल की बातचीत'}
                  </h4>
                </div>
                {recentChats.length > 6 && (
                  <Button variant="ghost" size="sm" className="text-primary hover:text-primary/80 font-bold">
                    {language === 'en' ? `View All (${recentChats.length})` : `सभी देखें (${recentChats.length})`}
                  </Button>
                )}
              </div>

              {/* Chat Cards Grid - Up to 2 rows */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {historyLoading ? (
                  // Loading state
                  [...Array(6)].map((_, idx) => (
                    <motion.div
                      key={idx}
                      variants={itemVariants}
                      className="relative"
                    >
                      <div className="relative bg-white dark:bg-slate-900 rounded-xl overflow-hidden shadow-md border border-slate-200 dark:border-slate-800 h-56 flex flex-col animate-pulse">
                        <div className="absolute left-0 top-0 bottom-0 w-8 bg-slate-100 dark:bg-slate-800 flex flex-col items-center justify-around py-4 border-r border-slate-200 dark:border-slate-700">
                          {[...Array(6)].map((_, i) => (
                            <div key={i} className="w-2.5 h-2.5 rounded-full bg-slate-300 dark:bg-slate-600" />
                          ))}
                        </div>
                        <div className="ml-8 p-5 flex-1 flex flex-col">
                          <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-20 mb-3"></div>
                          <div className="h-5 bg-slate-200 dark:bg-slate-700 rounded w-full mb-2"></div>
                          <div className="h-5 bg-slate-200 dark:bg-slate-700 rounded w-2/3"></div>
                        </div>
                      </div>
                    </motion.div>
                  ))
                ) : displayChats.length === 0 ? (
                  // Empty state
                  <motion.div
                    variants={itemVariants}
                    className="col-span-1 md:col-span-2 lg:col-span-3 text-center py-16 bg-white/40 dark:bg-white/5 rounded-2xl border border-dashed border-primary/20"
                  >
                    <div className="bg-primary/5 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4">
                      <MessageSquare className="h-10 w-10 text-primary/40" />
                    </div>
                    <h4 className="text-xl font-serif font-bold text-muted-foreground mb-2">
                      {language === 'en' ? 'Start Your Legal Research' : 'अपना कानूनी शोध शुरू करें'}
                    </h4>
                    <p className="text-muted-foreground/70 max-w-sm mx-auto">
                      {language === 'en' 
                        ? 'Ask any legal question to get expert analysis and see your history here.' 
                        : 'विशेषज्ञ विश्लेषण पाने और अपना इतिहास यहाँ देखने के लिए कोई भी कानूनी प्रश्न पूछें।'}
                    </p>
                  </motion.div>
                ) : (
                  // Real chat history
                  displayChats.map((chat) => (
                    <motion.div
                      key={chat.id}
                      variants={itemVariants}
                      whileHover={{ y: -5, boxShadow: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)" }}
                      className="relative group cursor-pointer"
                      onClick={() => onLoadSession?.(chat.id)}
                    >
                      {/* Notebook Style Card */}
                      <div className="relative bg-white dark:bg-[#1a1c23] rounded-xl overflow-hidden shadow-md border border-slate-200 dark:border-slate-800 h-56 flex flex-col transition-all duration-300 group-hover:border-primary/30">
                        {/* Spiral Bind */}
                        <div className="absolute left-0 top-0 bottom-0 w-8 bg-[#fdfaf5] dark:bg-[#252833] flex flex-col items-center justify-around py-4 border-r border-slate-200 dark:border-slate-700 z-10">
                          {[...Array(6)].map((_, i) => (
                            <div key={i} className="w-2.5 h-2.5 rounded-full bg-primary/10 dark:bg-white/5 shadow-inner border border-primary/20 dark:border-white/10" />
                          ))}
                        </div>

                        {/* Card Background Texture */}
                        <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[url('https://www.transparenttextures.com/patterns/notebook.png')]" />

                        {/* Content Area */}
                        <div className="ml-8 p-5 flex-1 flex flex-col relative z-20">
                          <div className="flex items-center gap-2 mb-3">
                            <div className="w-8 h-8 rounded-lg bg-primary/5 flex items-center justify-center text-sm">
                              {{
                                "Criminal": "🔴",
                                "Civil_Family": "👨‍👩‍👧",
                                "Corporate": "🏢",
                                "Consitutional": "📕",
                                "IT_Cyber": "💻",
                                "Environment": "🌳",
                                "Property": "🏠",
                                "Traffic": "🚗",
                                "all": "⚖️"
                              }[chat.domain || "all"] || "💬"}
                            </div>
                            <div className="flex flex-col">
                              <span className="text-[9px] uppercase tracking-[0.2em] text-primary font-bold opacity-70">
                                {chat.domain || (language === 'en' ? 'General' : 'सामान्य')}
                              </span>
                              <span className="text-[10px] text-muted-foreground font-medium">{chat.date}</span>
                            </div>
                            {chat.messageCount && (
                              <div className="ml-auto flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5">
                                <MessageSquare className="h-3 w-3 text-primary/60" />
                                <span className="text-[10px] text-muted-foreground font-bold">
                                  {chat.messageCount}
                                </span>
                              </div>
                            )}
                          </div>
                          
                          <h4 className="text-lg font-serif font-bold text-foreground group-hover:text-primary transition-colors leading-snug line-clamp-3 mb-4">
                            {chat.title}
                          </h4>
                          
                          {/* Indicator Lines */}
                          <div className="mt-auto flex gap-1">
                            <div className="h-1 rounded-full bg-primary/20 group-hover:bg-primary/40 transition-colors flex-1" />
                            <div className="h-1 rounded-full bg-primary/10 group-hover:bg-primary/20 transition-colors w-12" />
                            <div className="h-1 rounded-full bg-primary/5 group-hover:bg-primary/10 transition-colors w-8" />
                          </div>
                        </div>

                        {/* Hover Gradient */}
                        <div className="absolute inset-0 bg-gradient-to-br from-primary/0 via-primary/0 to-primary/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            </div>
          </div>
          
          {/* Quick Stats / Info */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { 
                label: language === 'en' ? 'Saved Statutes' : 'सहेजी गई धाराएं', 
                value: statsLoading ? '...' : `${stats.savedStatutes}+`, 
                icon: BookOpen 
              },
              { 
                label: language === 'en' ? 'Cases in Database' : 'डेटाबेस में केस', 
                value: statsLoading ? '...' : stats.casesAnalyzed.toString(), 
                icon: Clock 
              },
              { 
                label: language === 'en' ? 'Your Chats' : 'आपकी चैट', 
                value: historyLoading ? '...' : stats.activeSessions.toString(), 
                icon: History 
              },
            ].map((stat, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + i * 0.1 }}
                className="glass rounded-2xl p-6 flex items-center gap-4 border border-white/10"
              >
                <div className="p-3 bg-primary/10 rounded-xl">
                  {statsLoading || historyLoading ? (
                    <Loader2 className="h-6 w-6 text-primary animate-spin" />
                  ) : (
                    <stat.icon className="h-6 w-6 text-primary" />
                  )}
                </div>
                <div>
                  <p className="text-xs text-muted-foreground font-bold uppercase tracking-wider">{stat.label}</p>
                  <p className="text-2xl font-serif font-bold text-foreground">{stat.value}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Courtroom Immersive Scroll Experience at the bottom */}
      <SketchfabScrollExperience />
    </div>
  );
};
