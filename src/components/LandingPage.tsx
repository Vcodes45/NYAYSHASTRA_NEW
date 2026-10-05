import { useState, useEffect, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import {
    Scale,
    Brain,
    Globe,
    FileText,
    Shield,
    Sparkles,
    ArrowRight,
    Users,
    Building2,
    Gavel,
    BookOpen,
    Quote,
    ChevronRight,
    Play
} from 'lucide-react';
import { Button } from './ui/button';
import { Link } from 'react-router-dom';
import { Experience3D } from './3d/core/Experience3D';
import { SketchfabScrollExperience } from './3d/core/SketchfabScrollExperience';
import { MODEL_REGISTRY } from './3d/config/ModelRegistry';

interface LandingPageProps {
    language: 'en' | 'hi';
    onStartChat: (query?: string) => void;
    onLanguageChange?: (lang: 'en' | 'hi') => void;
}

// Animated counter component
const AnimatedCounter = ({ value, duration = 2000 }: { value: string; duration?: number }) => {
    const [count, setCount] = useState(0);
    const ref = useRef<HTMLDivElement>(null);
    const isInView = useInView(ref, { once: true });
    const numericValue = parseInt(value.replace(/\D/g, '')) || 0;
    const suffix = value.replace(/[0-9]/g, '');

    useEffect(() => {
        if (!isInView) return;

        let startTime: number;
        const animate = (timestamp: number) => {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            const easeOut = 1 - Math.pow(1 - progress, 3);
            setCount(Math.floor(easeOut * numericValue));

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        requestAnimationFrame(animate);
    }, [isInView, numericValue, duration]);

    return (
        <div ref={ref} className="text-4xl md:text-5xl font-bold text-primary font-mono counter-animate">
            {count}{suffix}
        </div>
    );
};

const stats = [
    { value: '500+', label: 'IPC Sections', labelHi: 'IPC धाराएं' },
    { value: '350+', label: 'BNS Sections', labelHi: 'BNS धाराएं' },
    { value: '100+', label: 'Landmark Cases', labelHi: 'ऐतिहासिक मामले' },
    { value: '2', label: 'Languages', labelHi: 'भाषाएं' }
];

const features = [
    {
        icon: Brain,
        title: 'Multi-Agent AI',
        titleHi: 'मल्टी-एजेंट AI',
        description: '7 specialized AI agents working in orchestration for comprehensive legal analysis',
        descriptionHi: '7 विशेषज्ञ AI एजेंट व्यापक कानूनी विश्लेषण के लिए समन्वय में काम कर रहे हैं'
    },
    {
        icon: Scale,
        title: 'IPC ↔ BNS Mapping',
        titleHi: 'IPC ↔ BNS मैपिंग',
        description: 'Automatic cross-referencing between old IPC and new BNS provisions',
        descriptionHi: 'पुराने IPC और नए BNS प्रावधानों के बीच स्वचालित क्रॉस-रेफ़रेंसिंग'
    },
    {
        icon: Globe,
        title: 'Bilingual Support',
        titleHi: 'द्विभाषी समर्थन',
        description: 'Seamless English and Hindi language support for wider accessibility',
        descriptionHi: 'व्यापक पहुंच के लिए निर्बाध अंग्रेजी और हिंदी भाषा समर्थन'
    },
    {
        icon: Shield,
        title: 'Verified Citations',
        titleHi: 'सत्यापित उद्धरण',
        description: 'All citations link directly to official government gazette sources',
        descriptionHi: 'सभी उद्धरण सीधे आधिकारिक सरकारी राजपत्र स्रोतों से जुड़ते हैं'
    },
    {
        icon: FileText,
        title: 'Document Analysis',
        titleHi: 'दस्तावेज़ विश्लेषण',
        description: 'Upload court orders and judgments for AI-powered summarization',
        descriptionHi: 'AI-संचालित सारांश के लिए कोर्ट आदेश और निर्णय अपलोड करें'
    },
    {
        icon: Gavel,
        title: 'Case Intelligence',
        titleHi: 'केस इंटेलिजेंस',
        description: 'Access Supreme Court and High Court judgments with smart search',
        descriptionHi: 'स्मार्ट सर्च के साथ सुप्रीम कोर्ट और हाई कोर्ट के निर्णय तक पहुंचें'
    }
];

const socialImpact = [
    {
        icon: Users,
        title: 'Access to Justice',
        titleHi: 'न्याय तक पहुंच',
        description: 'Democratizing legal knowledge for 1.4 billion Indians',
        descriptionHi: '1.4 अरब भारतीयों के लिए कानूनी ज्ञान का लोकतंत्रीकरण'
    },
    {
        icon: Building2,
        title: 'Rural Empowerment',
        titleHi: 'ग्रामीण सशक्तिकरण',
        description: 'Bridging the legal knowledge gap in rural communities',
        descriptionHi: 'ग्रामीण समुदायों में कानूनी ज्ञान की खाई को पाटना'
    },
    {
        icon: BookOpen,
        title: 'Legal Literacy',
        titleHi: 'कानूनी साक्षरता',
        description: 'Making complex laws understandable for everyone',
        descriptionHi: 'जटिल कानूनों को सभी के लिए समझने योग्य बनाना'
    }
];

const sampleQueries = [
    { query: 'What is Section 302 IPC and its BNS equivalent?', isHindi: false },
    { query: 'Explain the Vishaka Guidelines for workplace harassment', isHindi: false },
    { query: 'What are the punishments for cheating under Section 420?', isHindi: false },
    { query: 'धारा 376 में बलात्कार की सजा क्या है?', isHindi: true }
];

export const LandingPage = ({ language: initialLanguage, onStartChat, onLanguageChange }: LandingPageProps) => {
    const [language, setLanguage] = useState<'en' | 'hi'>(initialLanguage);

    const handleLanguageChange = (lang: 'en' | 'hi') => {
        setLanguage(lang);
        onLanguageChange?.(lang);
    };

    const containerVariants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: { staggerChildren: 0.1 }
        }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
    };

    return (
        <div className="min-h-screen texture-noise">
            {/* Navbar */}
            <motion.header
                initial={{ y: -20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.5 }}
                className="glass-strong border-b border-border/50 sticky top-0 z-50"
            >
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    {/* Logo */}
                    <Link to="/" className="flex items-center gap-3 group">
                        <motion.div
                            whileHover={{ scale: 1.05 }}
                            className="flex items-center gap-2"
                        >
                            <div className="relative">
                                <img 
                                    src="/national-emblem.png" 
                                    alt="NYAYASHASTRA Logo" 
                                    className="h-10 w-10 object-contain transition-transform group-hover:scale-105"
                                />
                            </div>
                            <div className="hidden sm:block">
                                <h1 className="text-xl font-serif font-bold tracking-wide">
                                    <span className="text-foreground">NYAYA</span>
                                    <span className="text-primary">SHASTRA</span>
                                </h1>
                                <p className="text-xs text-muted-foreground -mt-0.5 font-sans">
                                    {language === 'en' ? "India's Legal Intelligence" : 'भारत की कानूनी बुद्धिमत्ता'}
                                </p>
                            </div>
                        </motion.div>
                    </Link>

                    {/* Actions */}
                    <div className="flex items-center gap-3">
                        {/* Language Toggle */}
                        <div className="flex items-center gap-1 bg-muted/50 rounded-full p-1">
                            <Button
                                variant={language === 'en' ? 'default' : 'ghost'}
                                size="sm"
                                className="h-7 px-3 rounded-full text-xs font-medium"
                                onClick={() => handleLanguageChange('en')}
                            >
                                <Globe className="h-3 w-3 mr-1" />
                                EN
                            </Button>
                            <Button
                                variant={language === 'hi' ? 'default' : 'ghost'}
                                size="sm"
                                className="h-7 px-3 rounded-full text-xs text-hindi font-medium"
                                onClick={() => handleLanguageChange('hi')}
                            >
                                हि
                            </Button>
                        </div>

                        {/* Sign In Button */}
                        <Link to="/sign-in">
                            <Button size="sm" className="rounded-full px-5 gap-2 btn-shimmer">
                                {language === 'en' ? 'Sign In' : 'साइन इन'}
                                <ArrowRight className="h-4 w-4" />
                            </Button>
                        </Link>
                    </div>
                </div>
            </motion.header>

            {/* Hero Section */}
            <section className="relative py-24 md:py-32 px-4 overflow-hidden hero-pattern">
                {/* 3D Lady Justice Hero Background */}
                <div className="absolute right-0 top-0 w-full md:w-1/2 h-full pointer-events-none opacity-30 md:opacity-90 z-0">
                    <Experience3D config={MODEL_REGISTRY.ladyJustice} className="w-full h-full pointer-events-auto" />
                </div>

                {/* Background Emblem */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] opacity-[0.03] pointer-events-none z-0">
                    <img 
                        src="/national-emblem.png" 
                        alt="" 
                        className="w-full h-full object-contain grayscale"
                    />
                </div>

                <div className="container mx-auto max-w-5xl relative z-10">
                    <motion.div
                        initial="hidden"
                        animate="visible"
                        variants={containerVariants}
                        className="text-center"
                    >
                        {/* Badge */}
                        <motion.div
                            variants={itemVariants}
                            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-8"
                        >
                            <Sparkles className="h-4 w-4 text-primary" />
                            <span className="text-sm font-medium text-primary">
                                {language === 'en' ? "India's First AI Legal Assistant" : "भारत का पहला AI कानूनी सहायक"}
                            </span>
                        </motion.div>

                        {/* Logo */}
                        <motion.div
                            variants={itemVariants}
                            className="flex justify-center mb-8"
                        >
                            <div className="relative">
                                <img
                                    src="/national-emblem.png"
                                    alt="NYAYASHASTRA Logo" 
                                    className="h-28 w-28 md:h-36 md:w-36 object-contain"
                                />
                                <motion.div
                                    className="absolute inset-0 rounded-full opacity-30"
                                    animate={{
                                        boxShadow: [
                                            '0 0 20px hsl(28 70% 45% / 0.3)',
                                            '0 0 40px hsl(28 70% 45% / 0.5)',
                                            '0 0 20px hsl(28 70% 45% / 0.3)'
                                        ]
                                    }}
                                    transition={{ duration: 3, repeat: Infinity }}
                                />
                            </div>
                        </motion.div>

                        {/* Main Title */}
                        <motion.h1
                            variants={itemVariants}
                            className="text-5xl md:text-7xl lg:text-8xl font-serif font-bold mb-6 tracking-tight"
                        >
                            <span className="text-foreground">NYAYA</span>
                            <span className="gradient-text-gold">SHASTRA</span>
                        </motion.h1>

                        <motion.p
                            variants={itemVariants}
                            className="text-xl md:text-2xl text-muted-foreground mb-3 max-w-3xl mx-auto font-serif italic"
                        >
                            {language === 'en'
                                ? 'AI-Powered Legal Helper for India'
                                : 'भारत के लिए AI-संचालित कानूनी सहायक'}
                        </motion.p>

                        <motion.p
                            variants={itemVariants}
                            className="text-base md:text-lg text-muted-foreground mb-10 max-w-2xl mx-auto"
                        >
                            {language === 'en'
                                ? 'Get instant, accurate, and bilingual answers about IPC, BNS, and Indian law with verified citations from official sources.'
                                : 'आधिकारिक स्रोतों से सत्यापित उद्धरणों के साथ IPC, BNS और भारतीय कानून के बारे में तत्काल, सटीक और द्विभाषी उत्तर प्राप्त करें।'}
                        </motion.p>

                        {/* CTA Buttons */}
                        <motion.div
                            variants={itemVariants}
                            className="flex flex-col sm:flex-row gap-4 justify-center mb-16"
                        >
                            <Button
                                size="lg"
                                className="text-lg px-8 py-6 rounded-xl glow-primary btn-shimmer"
                                onClick={() => onStartChat()}
                            >
                                {language === 'en' ? 'Start Legal Query' : 'कानूनी प्रश्न शुरू करें'}
                                <ArrowRight className="ml-2 h-5 w-5" />
                            </Button>
                            <Button
                                size="lg"
                                variant="outline"
                                className="text-lg px-8 py-6 rounded-xl group"
                            >
                                <Play className="mr-2 h-5 w-5 group-hover:text-primary transition-colors" />
                                {language === 'en' ? 'Watch Demo' : 'डेमो देखें'}
                            </Button>
                        </motion.div>

                        {/* Stats */}
                        <motion.div
                            variants={itemVariants}
                            className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 max-w-4xl mx-auto"
                        >
                            {stats.map((stat, idx) => (
                                <motion.div
                                    key={idx}
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    transition={{ delay: 0.5 + idx * 0.1 }}
                                    className="stat-card rounded-xl p-5 text-center"
                                >
                                    <AnimatedCounter value={stat.value} />
                                    <div className="text-sm text-muted-foreground mt-1 font-medium">
                                        {language === 'hi' ? stat.labelHi : stat.label}
                                    </div>
                                </motion.div>
                            ))}
                        </motion.div>
                    </motion.div>
                </div>
            </section>

            {/* Divider */}
            <div className="container max-w-4xl mx-auto px-4">
                <div className="double-divider" />
            </div>

            {/* Features Section */}
            <section className="py-20 md:py-24 px-4 relative overflow-hidden">
                <div className="container mx-auto max-w-6xl relative z-10">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-14"
                    >
                        <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
                            {language === 'en' ? 'Powerful Features' : 'शक्तिशाली विशेषताएं'}
                        </h2>
                        <p className="text-muted-foreground max-w-2xl mx-auto text-lg">
                            {language === 'en'
                                ? 'Built with cutting-edge AI technology for accurate legal assistance'
                                : 'सटीक कानूनी सहायता के लिए अत्याधुनिक AI तकनीक के साथ निर्मित'}
                        </p>
                    </motion.div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {features.map((feature, idx) => (
                            <motion.div
                                key={idx}
                                initial={{ opacity: 0, y: 30 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: idx * 0.08 }}
                                className="feature-card p-6 group cursor-default"
                            >
                                <div className="icon-container w-fit mb-5">
                                    <feature.icon className="h-6 w-6 text-primary" />
                                </div>
                                <h3 className="text-lg font-serif font-semibold mb-2 group-hover:text-primary transition-colors">
                                    {language === 'hi' ? feature.titleHi : feature.title}
                                </h3>
                                <p className="text-sm text-muted-foreground leading-relaxed">
                                    {language === 'hi' ? feature.descriptionHi : feature.description}
                                </p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Divider */}
            <div className="container max-w-4xl mx-auto px-4">
                <div className="double-divider" />
            </div>

            {/* Social Impact Section */}
            <section className="py-20 md:py-24 px-4">
                <div className="container mx-auto max-w-6xl">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-14"
                    >
                        <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4 font-serif">
                            {language === 'en' ? 'Social Impact' : 'सामाजिक प्रभाव'}
                        </h2>
                        <p className="text-muted-foreground max-w-2xl mx-auto text-lg">
                            {language === 'en'
                                ? 'Democratizing access to legal knowledge across India'
                                : 'पूरे भारत में कानूनी ज्ञान तक पहुंच का लोकतंत्रीकरण'}
                        </p>
                    </motion.div>

                    <div className="grid md:grid-cols-3 gap-8 mb-14">
                        {socialImpact.map((item, idx) => (
                            <motion.div
                                key={idx}
                                initial={{ opacity: 0, scale: 0.95 }}
                                whileInView={{ opacity: 1, scale: 1 }}
                                viewport={{ once: true }}
                                transition={{ delay: idx * 0.12 }}
                                className="text-center p-8 rounded-2xl card-elevated"
                            >
                                <div className="icon-container w-fit mx-auto mb-5">
                                    <item.icon className="h-8 w-8 text-primary" />
                                </div>
                                <h3 className="text-xl font-semibold mb-3">
                                    {language === 'hi' ? item.titleHi : item.title}
                                </h3>
                                <p className="text-muted-foreground">
                                    {language === 'hi' ? item.descriptionHi : item.description}
                                </p>
                            </motion.div>
                        ))}
                    </div>

                    {/* Impact Quote */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="card-elevated rounded-2xl p-8 md:p-10 text-center max-w-3xl mx-auto"
                    >
                        <Quote className="h-10 w-10 text-primary/40 mx-auto mb-5" />
                        <blockquote className="text-xl md:text-2xl italic text-foreground mb-4 font-serif">
                            {language === 'en'
                                ? '"Justice delayed is justice denied. NYAYASHASTRA brings instant legal clarity to every Indian citizen."'
                                : '"न्याय में देरी न्याय से वंचित करना है। NYAYASHASTRA हर भारतीय नागरिक के लिए तत्काल कानूनी स्पष्टता लाता है।"'}
                        </blockquote>
                    </motion.div>
                </div>
            </section>

            {/* Try It Section */}
            <section className="py-20 md:py-24 px-4 bg-muted/30">
                <div className="container mx-auto max-w-4xl">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-10"
                    >
                        <h2 className="text-3xl md:text-4xl font-bold mb-4">
                            {language === 'en' ? 'Try It Now' : 'अभी प्रयास करें'}
                        </h2>
                        <p className="text-muted-foreground text-lg">
                            {language === 'en'
                                ? 'Click on any question to get started instantly'
                                : 'तुरंत शुरू करने के लिए किसी भी प्रश्न पर क्लिक करें'}
                        </p>
                    </motion.div>

                    <div className="grid gap-3">
                        {sampleQueries.map((item, idx) => (
                            <motion.button
                                key={idx}
                                initial={{ opacity: 0, x: -20 }}
                                whileInView={{ opacity: 1, x: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: idx * 0.08 }}
                                onClick={() => onStartChat(item.query)}
                                className="query-button group"
                            >
                                <span className={`text-foreground group-hover:text-primary transition-colors ${item.isHindi ? 'text-hindi' : ''}`}>
                                    {item.query}
                                </span>
                                <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                            </motion.button>
                        ))}
                    </div>
                </div>
            </section>

            {/* Courtroom Immersive Scroll Experience */}
            <SketchfabScrollExperience />

            {/* Footer */}
            <footer className="py-10 px-4 border-t border-border bg-card/50">
                <div className="container mx-auto max-w-6xl">
                    <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                        {/* Logo */}
                        <div className="flex items-center gap-2">
                            <img
                                src="/national-emblem.png"
                                alt="NYAYASHASTRA"
                                className="h-8 w-8 object-contain opacity-60"
                            />
                            <span className="text-sm font-serif font-semibold text-muted-foreground">
                                NYAYASHASTRA
                            </span>
                        </div>

                        {/* Disclaimer */}
                        <p className="text-sm text-muted-foreground text-center">
                            {language === 'en'
                                ? '⚖️ This tool is for informational purposes only and does not constitute legal advice.'
                                : '⚖️ यह उपकरण केवल सूचनात्मक उद्देश्यों के लिए है और कानूनी सलाह नहीं है।'}
                        </p>

                        {/* Copyright */}
                        <p className="text-xs text-muted-foreground">
                            © 2024 NYAYASHASTRA
                        </p>
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default LandingPage;
