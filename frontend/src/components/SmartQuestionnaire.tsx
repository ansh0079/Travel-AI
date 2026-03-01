'use client';

import { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TravelPreferences } from '@/services/api';

// ─── Types ────────────────────────────────────────────────────────────────────

type QuestionType = 'text' | 'date-range' | 'single-choice' | 'multi-choice' | 'boolean' | 'number' | 'slider';

interface Option {
    value: string;
    label: string;
    icon?: string;
    desc?: string;
}

interface Question {
    id: string;
    text: string;
    subtext?: string;
    field: keyof TravelPreferences | string;           // field to write into context
    type: QuestionType;
    options?: Option[];
    min?: number;
    max?: number;
    step?: number;
    unit?: string;
    placeholder?: string;
    required?: boolean;
    /** Dynamic branch: given current answer, return extra question IDs to inject next */
    branch?: (answer: unknown, ctx: Partial<TravelPreferences>) => string[];
}

interface _Answer {
    questionId: string;
    value: unknown;
}

// ─── Branch helpers ───────────────────────────────────────────────────────────

/** Returns extra question IDs when user says they have kids */
function kidsFollowUps(): string[] {
    return ['kids_ages', 'kids_bedtime', 'kids_theme_parks'];
}

/** Returns extra question IDs for food lovers */
function foodFollowUps(): string[] {
    return ['dietary_restrictions', 'cuisine_preferences'];
}

/** Returns extra question IDs for luxury budget */
function luxuryFollowUps(): string[] {
    return ['transfer_preference', 'butler_service', 'fine_dining'];
}

/** Returns extra question IDs for group/friends travel */
function friendsFollowUps(): string[] {
    return ['nightlife_importance', 'room_arrangement'];
}

/** Returns extra question IDs for couple travel */
function coupleFollowUps(): string[] {
    return ['romantic_experiences', 'couple_activities'];
}

/** Returns extra question IDs when accessibility needs selected */
function accessibilityFollowUps(): string[] {
    return ['accessibility_detail'];
}

/** Returns extra question IDs when adventure is an interest */
function adventureFollowUps(): string[] {
    return ['adventure_level'];
}

// ─── Master question bank ─────────────────────────────────────────────────────

const QUESTION_BANK: Record<string, Question> = {

    // ── Core questions (always shown) ──────────────────────────────────────────

    origin: {
        id: 'origin',
        text: '✈️ Where are you flying from?',
        subtext: 'Your departure city or airport',
        field: 'origin',
        type: 'text',
        placeholder: 'e.g. London, New York, Dubai…',
        required: true,
    },

    travel_dates: {
        id: 'travel_dates',
        text: '📅 When are you travelling?',
        subtext: 'Pick your departure and return dates',
        field: 'travel_start',            // we handle both start & end inside render
        type: 'date-range',
        required: true,
    },

    trip_duration: {
        id: 'trip_duration',
        text: '⏱️ How many nights are you planning to stay?',
        field: 'notes',                   // packed into notes; used by agent context
        type: 'slider',
        min: 2,
        max: 30,
        step: 1,
        unit: 'nights',
    },

    traveling_with: {
        id: 'traveling_with',
        text: '👥 Who are you travelling with?',
        field: 'traveling_with',
        type: 'single-choice',
        required: true,
        options: [
            { value: 'solo', icon: '🧑', label: 'Solo', desc: 'Just me!' },
            { value: 'couple', icon: '💑', label: 'Couple', desc: 'Romantic getaway' },
            { value: 'family', icon: '👨‍👩‍👧‍👦', label: 'Family', desc: 'Kids in tow' },
            { value: 'group', icon: '👥', label: 'Friends', desc: 'Group adventure' },
        ],
        branch: (answer) => {
            if (answer === 'family') return kidsFollowUps();
            if (answer === 'group') return friendsFollowUps();
            if (answer === 'couple') return coupleFollowUps();
            return [];
        },
    },

    has_kids: {
        id: 'has_kids',
        text: '🧒 Are children travelling with you?',
        field: 'has_kids',
        type: 'boolean',
        branch: (answer) => (answer === true ? kidsFollowUps() : []),
    },

    budget_level: {
        id: 'budget_level',
        text: '💰 What\'s your budget style?',
        subtext: 'This shapes accommodation, dining & activities',
        field: 'budget_level',
        type: 'single-choice',
        required: true,
        options: [
            { value: 'low', icon: '🎒', label: 'Budget', desc: 'Hostels, street food' },
            { value: 'moderate', icon: '🏨', label: 'Moderate', desc: '3-star, local restaurants' },
            { value: 'high', icon: '🌟', label: 'Comfort', desc: '4-star hotels & dining' },
            { value: 'luxury', icon: '💎', label: 'Luxury', desc: '5-star, private transfers' },
        ],
        branch: (answer) => (answer === 'luxury' ? luxuryFollowUps() : []),
    },

    interests: {
        id: 'interests',
        text: '🎯 What excites you most? (pick all that apply)',
        subtext: 'The more you pick, the smarter your results',
        field: 'interests',
        type: 'multi-choice',
        required: true,
        options: [
            { value: 'beach', icon: '🏖️', label: 'Beaches' },
            { value: 'mountain', icon: '🏔️', label: 'Mountains' },
            { value: 'city', icon: '🏙️', label: 'City Life' },
            { value: 'history', icon: '🏛️', label: 'History' },
            { value: 'nature', icon: '🌿', label: 'Nature' },
            { value: 'adventure', icon: '🎿', label: 'Adventure' },
            { value: 'food', icon: '🍜', label: 'Food & Dining' },
            { value: 'culture', icon: '🎭', label: 'Culture & Arts' },
            { value: 'relaxation', icon: '🧘', label: 'Wellness' },
            { value: 'nightlife', icon: '🌃', label: 'Nightlife' },
            { value: 'shopping', icon: '🛍️', label: 'Shopping' },
            { value: 'music', icon: '🎵', label: 'Music & Festivals' },
            { value: 'photography', icon: '📸', label: 'Photography' },
            { value: 'wine', icon: '🍷', label: 'Wine & Drinks' },
            { value: 'sports', icon: '⚽', label: 'Sports' },
        ],
        branch: (answers) => {
            const arr = answers as string[];
            const extra: string[] = [];
            if (arr.includes('food')) extra.push(...foodFollowUps());
            if (arr.includes('adventure')) extra.push(...adventureFollowUps());
            return extra;
        },
    },

    weather_preference: {
        id: 'weather_preference',
        text: '🌤️ What weather suits you best?',
        field: 'weather_preference',
        type: 'single-choice',
        options: [
            { value: 'hot', icon: '☀️', label: 'Hot', desc: '30°C+' },
            { value: 'warm', icon: '🌤️', label: 'Warm', desc: '20–30°C' },
            { value: 'mild', icon: '⛅', label: 'Mild', desc: '10–20°C' },
            { value: 'cold', icon: '❄️', label: 'Cold', desc: '0–10°C' },
            { value: 'snow', icon: '🌨️', label: 'Snow', desc: 'Winter magic' },
        ],
    },

    passport_country: {
        id: 'passport_country',
        text: '🛂 Which passport do you hold?',
        subtext: 'Helps us check visa requirements for you',
        field: 'passport_country',
        type: 'single-choice',
        options: [
            { value: 'US', label: '🇺🇸 United States' },
            { value: 'UK', label: '🇬🇧 United Kingdom' },
            { value: 'CA', label: '🇨🇦 Canada' },
            { value: 'AU', label: '🇦🇺 Australia' },
            { value: 'DE', label: '🇩🇪 Germany' },
            { value: 'FR', label: '🇫🇷 France' },
            { value: 'JP', label: '🇯🇵 Japan' },
            { value: 'IN', label: '🇮🇳 India' },
            { value: 'AE', label: '🇦🇪 UAE' },
            { value: 'SG', label: '🇸🇬 Singapore' },
            { value: 'BR', label: '🇧🇷 Brazil' },
            { value: 'Other', label: '🌍 Other' },
        ],
    },

    visa_preference: {
        id: 'visa_preference',
        text: '📋 Visa preference?',
        field: 'visa_preference',
        type: 'single-choice',
        options: [
            { value: 'visa_free', icon: '✅', label: 'Visa-free only', desc: 'No paperwork needed' },
            { value: 'visa_on_arrival', icon: '🛂', label: 'Visa on arrival OK', desc: 'Get it at the airport' },
            { value: 'evisa_ok', icon: '📱', label: 'eVisa OK', desc: 'Apply online in advance' },
        ],
    },

    max_flight_duration: {
        id: 'max_flight_duration',
        text: '🕐 What\'s the longest flight you\'re comfortable with?',
        field: 'max_flight_duration',
        type: 'slider',
        min: 2,
        max: 24,
        step: 1,
        unit: 'hours',
    },

    accessibility_needs: {
        id: 'accessibility_needs',
        text: '♿ Any accessibility requirements?',
        subtext: 'We\'ll only suggest places that can accommodate you',
        field: 'accessibility_needs',
        type: 'multi-choice',
        options: [
            { value: 'none', label: '✅ None' },
            { value: 'wheelchair', label: '♿ Wheelchair accessible' },
            { value: 'limited_walking', label: '🚶 Limited walking' },
            { value: 'visual', label: '👁️ Visual impairment support' },
            { value: 'quiet_spaces', label: '🤫 Quiet/sensory-friendly' },
        ],
        branch: (answers) => {
            const arr = answers as string[];
            return arr.length > 0 && !arr.includes('none') ? accessibilityFollowUps() : [];
        },
    },

    // ── Conditional / branched questions ──────────────────────────────────────

    kids_ages: {
        id: 'kids_ages',
        text: '🎈 What are the ages of your children?',
        subtext: 'Helps us find age-appropriate activities and child-friendly hotels',
        field: 'kids_ages',
        type: 'text',
        placeholder: 'e.g. 3, 7, 12',
    },

    kids_bedtime: {
        id: 'kids_bedtime',
        text: '🌙 Do the kids have early bedtimes?',
        subtext: 'Affects evening activity and dinner planning',
        field: 'notes',
        type: 'boolean',
    },

    kids_theme_parks: {
        id: 'kids_theme_parks',
        text: '🎢 Interested in theme parks or child-focused attractions?',
        field: 'notes',
        type: 'boolean',
    },

    nightlife_importance: {
        id: 'nightlife_importance',
        text: '🌆 Is nightlife an important part of this trip?',
        subtext: 'We\'ll include bars, clubs and late-night spots',
        field: 'notes',
        type: 'boolean',
    },

    room_arrangement: {
        id: 'room_arrangement',
        text: '🛏️ Room preference for the group?',
        field: 'notes',
        type: 'single-choice',
        options: [
            { value: 'shared', icon: '🏠', label: 'Shared rooms', desc: 'Budget-friendly' },
            { value: 'private', icon: '🚪', label: 'Private rooms', desc: 'More space & privacy' },
            { value: 'mix', icon: '🤝', label: 'Mix of both', desc: 'Flexible' },
        ],
    },

    romantic_experiences: {
        id: 'romantic_experiences',
        text: '💕 Any romantic experiences you\'d love?',
        field: 'notes',
        type: 'multi-choice',
        options: [
            { value: 'sunset_views', icon: '🌅', label: 'Sunset viewpoints' },
            { value: 'candlelit_dining', icon: '🕯️', label: 'Candlelit dining' },
            { value: 'couples_spa', icon: '💆', label: 'Couples spa' },
            { value: 'champagne', icon: '🥂', label: 'Champagne experiences' },
            { value: 'private_tours', icon: '🗺️', label: 'Private guided tours' },
        ],
    },

    couple_activities: {
        id: 'couple_activities',
        text: '🌹 What\'s the vibe for your couple\'s trip?',
        field: 'trip_type' as keyof TravelPreferences,
        type: 'single-choice',
        options: [
            { value: 'romantic', icon: '❤️', label: 'Romantic & intimate' },
            { value: 'adventure', icon: '🧗', label: 'Adventure together' },
            { value: 'relaxation', icon: '🧘', label: 'Relax & recharge' },
            { value: 'cultural', icon: '🏛️', label: 'Explore culture & art' },
        ],
    },

    dietary_restrictions: {
        id: 'dietary_restrictions',
        text: '🍽️ Any dietary restrictions?',
        subtext: 'We\'ll ensure restaurant recommendations accommodate you',
        field: 'dietary_restrictions',
        type: 'multi-choice',
        options: [
            { value: 'none', label: '✅ None' },
            { value: 'vegetarian', label: '🥗 Vegetarian' },
            { value: 'vegan', label: '🌱 Vegan' },
            { value: 'halal', label: '🌙 Halal' },
            { value: 'kosher', label: '✡️  Kosher' },
            { value: 'gluten_free', label: '🌾 Gluten-free' },
            { value: 'nut_free', label: '🥜 Nut-free' },
            { value: 'dairy_free', label: '🥛 Dairy-free' },
        ],
    },

    cuisine_preferences: {
        id: 'cuisine_preferences',
        text: '🌏 Any cuisines you\'re excited to try?',
        subtext: 'Tell us what excites your taste buds',
        field: 'notes',
        type: 'text',
        placeholder: 'e.g. Japanese, Italian, street food…',
    },

    adventure_level: {
        id: 'adventure_level',
        text: '⚡ How intense do you want your adventures?',
        field: 'pace_preference' as keyof TravelPreferences,
        type: 'single-choice',
        options: [
            { value: 'relaxed', icon: '🌊', label: 'Light', desc: 'Hiking, cycling, snorkelling' },
            { value: 'moderate', icon: '🧗', label: 'Moderate', desc: 'Rafting, zip-lining, safaris' },
            { value: 'busy', icon: '🪂', label: 'Extreme', desc: 'Skydiving, bungee, expeditions' },
        ],
    },

    transfer_preference: {
        id: 'transfer_preference',
        text: '🚘 How would you like to get around?',
        field: 'notes',
        type: 'single-choice',
        options: [
            { value: 'private', icon: '🚙', label: 'Private transfers', desc: 'Door-to-door luxury' },
            { value: 'self_drive', icon: '🗝️', label: 'Self-drive', desc: 'Freedom & flexibility' },
            { value: 'mix', icon: '🤝', label: 'Mix of both', desc: 'Best of both worlds' },
        ],
    },

    butler_service: {
        id: 'butler_service',
        text: '🛎️ Is butler or dedicated concierge service important?',
        field: 'notes',
        type: 'boolean',
    },

    fine_dining: {
        id: 'fine_dining',
        text: '⭐ Should we prioritise Michelin-starred or fine dining restaurants?',
        field: 'notes',
        type: 'boolean',
    },

    accessibility_detail: {
        id: 'accessibility_detail',
        text: '🔍 Any specific accessibility details we should know?',
        subtext: 'Helps us find exactly the right venues and hotels',
        field: 'notes',
        type: 'text',
        placeholder: 'e.g. need hotel ground floor, require wide corridors…',
    },

    pace_preference: {
        id: 'pace_preference',
        text: '🗓️ What pace suits your trip?',
        field: 'pace_preference' as keyof TravelPreferences,
        type: 'single-choice',
        options: [
            { value: 'relaxed', icon: '🌅', label: 'Relaxed', desc: 'Few highlights, plenty of downtime' },
            { value: 'moderate', icon: '☕', label: 'Balanced', desc: 'Good mix of sights & rest' },
            { value: 'busy', icon: '🏃', label: 'Packed', desc: 'See as much as possible' },
        ],
    },

    destinations: {
        id: 'destinations',
        text: '🗺️ Do you have specific destinations in mind? (optional)',
        subtext: 'Leave blank and our AI will suggest the best matches',
        field: 'destinations',
        type: 'text',
        placeholder: 'e.g. Bali, Tokyo, Santorini — or leave empty for AI picks',
    },
};

// ─── Core question flow (always asked) ────────────────────────────────────────

const CORE_FLOW: string[] = [
    'origin',
    'travel_dates',
    'traveling_with',
    'budget_level',
    'interests',
    'weather_preference',
    'passport_country',
    'visa_preference',
    'max_flight_duration',
    'accessibility_needs',
    'pace_preference',
    'destinations',
];

// ─── Props ────────────────────────────────────────────────────────────────────

interface SmartQuestionnaireProps {
    onComplete: (preferences: TravelPreferences) => void;
    onCancel?: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function SmartQuestionnaire({ onComplete, onCancel }: SmartQuestionnaireProps) {
    // Build initial question queue from core flow
    const [questionQueue, setQuestionQueue] = useState<string[]>(CORE_FLOW);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [answers, setAnswers] = useState<Record<string, unknown>>({});
    const [context, setContext] = useState<Partial<TravelPreferences>>({});
    const [injectedIds, setInjectedIds] = useState<Set<string>>(new Set()); // track already injected
    const [direction, setDirection] = useState<'fwd' | 'bwd'>('fwd');
    const [dateStart, setDateStart] = useState('');
    const [dateEnd, setDateEnd] = useState('');
    const [sliderVal, setSliderVal] = useState<Record<string, number>>({});
    const [textVal, setTextVal] = useState<Record<string, string>>({});
    const _lastAnsweredRef = useRef<string>('');

    const currentId = questionQueue[currentIndex];
    const question = QUESTION_BANK[currentId];
    const progress = Math.round(((currentIndex + 1) / questionQueue.length) * 100);
    const isLast = currentIndex === questionQueue.length - 1;

    // ── Helpers ─────────────────────────────────────────────────────────────────

    const _currentAnswer = answers[currentId];

    const canAdvance = useCallback(() => {
        if (!question) return false;
        if (!question.required) return true;
        const a = answers[currentId];
        if (question.type === 'date-range') return !!dateStart && !!dateEnd;
        if (question.type === 'multi-choice') return Array.isArray(a) && (a as string[]).length > 0;
        if (question.type === 'boolean') return a !== undefined && a !== null;
        if (question.type === 'text') return typeof a === 'string' && a.trim().length > 0;
        return a !== undefined && a !== null;
    }, [answers, currentId, question, dateStart, dateEnd]);

    // Inject branch follow-ups right after the current position (deduped)
    const maybeInjectBranches = useCallback((questionId: string, answer: unknown, currentCtx: Partial<TravelPreferences>) => {
        const q = QUESTION_BANK[questionId];
        if (!q?.branch) return;
        const newIds = q.branch(answer, currentCtx).filter(
            (id) => !injectedIds.has(id) && QUESTION_BANK[id]
        );
        if (newIds.length === 0) return;

        setInjectedIds(prev => {
            const next = new Set(prev);
            newIds.forEach(id => next.add(id));
            return next;
        });

        setQuestionQueue(prev => {
            const insertAt = prev.indexOf(questionId) + 1;
            const updated = [...prev];
            updated.splice(insertAt, 0, ...newIds);
            return updated;
        });
    }, [injectedIds]);

    // ── Write answer to context ──────────────────────────────────────────────────

    const commitAnswer = useCallback((questionId: string, value: unknown) => {
        const q = QUESTION_BANK[questionId];
        if (!q) return;

        setAnswers(prev => ({ ...prev, [questionId]: value }));

        // Map the answer directly into TravelPreferences context
        setContext(prev => {
            const next = { ...prev } as any;

            if (q.type === 'date-range') {
                // handled separately via dateStart / dateEnd
                return next;
            }

            const field = q.field as string;

            if (field === 'notes') {
                // Append as structured note
                const noteKey = q.id;
                const existing: string = next.notes || '';
                const newNote = `[${noteKey}=${JSON.stringify(value)}]`;
                if (!existing.includes(`[${noteKey}=`)) {
                    next.notes = existing ? `${existing} ${newNote}` : newNote;
                } else {
                    next.notes = existing.replace(/\[${noteKey}=[^\]]*\]/, newNote);
                }
            } else if (field === 'has_kids') {
                next.has_kids = value as boolean;
            } else if (field === 'kids_ages') {
                next.kids_ages = (value as string).split(',').map((s: string) => s.trim());
            } else if (field === 'destinations') {
                next.destinations = (value as string)
                    ? (value as string).split(',').map((s: string) => s.trim()).filter(Boolean)
                    : [];
            } else if (field === 'interests') {
                next.interests = value as string[];
            } else if (field === 'dietary_restrictions') {
                next.dietary_restrictions = (value as string[]).filter(v => v !== 'none');
            } else if (field === 'accessibility_needs') {
                next.accessibility_needs = (value as string[]).filter(v => v !== 'none');
            } else {
                next[field] = value;
            }
            return next;
        });
    }, []);

    // ── Navigation ───────────────────────────────────────────────────────────────

    const goNext = useCallback(() => {
        if (!canAdvance()) return;

        let value = answers[currentId];

        // Handle special types
        if (question.type === 'date-range') {
            value = { start: dateStart, end: dateEnd };
            setAnswers(prev => ({ ...prev, [currentId]: value }));
            setContext(prev => ({ ...prev, travel_start: dateStart, travel_end: dateEnd }));
        } else if (question.type === 'slider') {
            value = sliderVal[currentId] ?? question.min ?? 0;
            commitAnswer(currentId, value);
        } else if (question.type === 'text') {
            value = textVal[currentId] ?? '';
            commitAnswer(currentId, value);
        }

        // Trigger branching
        maybeInjectBranches(currentId, value, context);

        setDirection('fwd');
        setCurrentIndex(i => i + 1);
    }, [canAdvance, answers, currentId, question, dateStart, dateEnd, sliderVal, textVal, context, commitAnswer, maybeInjectBranches]);

    const goPrev = () => {
        if (currentIndex === 0) return;
        setDirection('bwd');
        setCurrentIndex(i => i - 1);
    };

    const skip = () => {
        setDirection('fwd');
        setCurrentIndex(i => i + 1);
    };

    const handleFinish = () => {
        // Commit any pending slider/text for last question
        const finalCtx = { ...context };
        if (question.type === 'slider') {
            const val = sliderVal[currentId] ?? question.min ?? 0;
            (finalCtx as any)[question.field] = val;
        }
        if (question.type === 'text') {
            const val = textVal[currentId] ?? '';
            if (val) (finalCtx as any)[question.field] = val;
        }
        onComplete(finalCtx as TravelPreferences);
    };

    // ── Render helpers ───────────────────────────────────────────────────────────

    const handleSingleChoice = (value: string) => {
        commitAnswer(currentId, value);
    };

    const handleMultiChoice = (value: string) => {
        const current = (answers[currentId] as string[]) || [];
        const newVal = current.includes(value)
            ? current.filter(v => v !== value)
            : [...current, value];
        commitAnswer(currentId, newVal);
    };

    const handleBoolean = (value: boolean) => {
        commitAnswer(currentId, value);
    };

    if (!question) return null;

    // ── Render question content ──────────────────────────────────────────────────

    const renderQuestionContent = () => {
        switch (question.type) {

            case 'text':
                return (
                    <input
                        type="text"
                        value={textVal[currentId] ?? (answers[currentId] as string) ?? ''}
                        onChange={e => {
                            setTextVal(prev => ({ ...prev, [currentId]: e.target.value }));
                            if (question.required) {
                                // commit optimistically so canAdvance works
                                setAnswers(prev => ({ ...prev, [currentId]: e.target.value }));
                            }
                        }}
                        placeholder={question.placeholder}
                        className="w-full px-5 py-4 text-lg border-2 border-gray-200 rounded-2xl
                       focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100
                       outline-none transition-all placeholder-gray-400"
                        autoFocus
                        onKeyDown={e => { if (e.key === 'Enter') canAdvance() && goNext(); }}
                    />
                );

            case 'date-range':
                return (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {(['Departure', 'Return'] as const).map((label, i) => (
                            <div key={label} className="flex flex-col gap-1">
                                <label className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
                                    {label} date
                                </label>
                                <input
                                    type="date"
                                    value={i === 0 ? dateStart : dateEnd}
                                    min={i === 0 ? new Date().toISOString().split('T')[0] : dateStart}
                                    onChange={e => i === 0 ? setDateStart(e.target.value) : setDateEnd(e.target.value)}
                                    className="px-5 py-4 text-base border-2 border-gray-200 rounded-2xl
                             focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100
                             outline-none transition-all cursor-pointer"
                                />
                            </div>
                        ))}
                    </div>
                );

            case 'single-choice':
                return (
                    <div className="grid grid-cols-2 gap-3">
                        {question.options?.map(opt => {
                            const selected = answers[currentId] === opt.value;
                            return (
                                <button
                                    key={opt.value}
                                    type="button"
                                    onClick={() => handleSingleChoice(opt.value)}
                                    className={`p-4 rounded-2xl border-2 text-left transition-all duration-200
                    ${selected
                                            ? 'border-indigo-500 bg-indigo-50 shadow-md scale-[1.02]'
                                            : 'border-gray-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/40'
                                        }`}
                                >
                                    {opt.icon && <div className="text-3xl mb-2 leading-none">{opt.icon}</div>}
                                    <div className={`font-semibold text-sm ${selected ? 'text-indigo-700' : 'text-gray-800'}`}>
                                        {opt.label}
                                    </div>
                                    {opt.desc && (
                                        <div className="text-xs text-gray-500 mt-0.5">{opt.desc}</div>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                );

            case 'multi-choice': {
                const selected = (answers[currentId] as string[]) || [];
                return (
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        {question.options?.map(opt => {
                            const isSelected = selected.includes(opt.value);
                            return (
                                <button
                                    key={opt.value}
                                    type="button"
                                    onClick={() => handleMultiChoice(opt.value)}
                                    className={`p-3 rounded-2xl border-2 text-left transition-all duration-200
                    ${isSelected
                                            ? 'border-indigo-500 bg-indigo-50 shadow-md'
                                            : 'border-gray-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/40'
                                        }`}
                                >
                                    {opt.icon && <span className="text-2xl mr-2">{opt.icon}</span>}
                                    <span className={`text-sm font-medium ${isSelected ? 'text-indigo-700' : 'text-gray-700'}`}>
                                        {opt.label}
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                );
            }

            case 'boolean':
                return (
                    <div className="grid grid-cols-2 gap-4">
                        {[
                            { value: true, icon: '✅', label: 'Yes' },
                            { value: false, icon: '❌', label: 'No' },
                        ].map(opt => {
                            const selected = answers[currentId] === opt.value;
                            return (
                                <button
                                    key={String(opt.value)}
                                    type="button"
                                    onClick={() => handleBoolean(opt.value as boolean)}
                                    className={`py-6 rounded-2xl border-2 flex flex-col items-center gap-2 transition-all
                    ${selected
                                            ? 'border-indigo-500 bg-indigo-50 shadow-md scale-[1.02]'
                                            : 'border-gray-200 bg-white hover:border-indigo-300'
                                        }`}
                                >
                                    <span className="text-4xl">{opt.icon}</span>
                                    <span className={`font-bold text-lg ${selected ? 'text-indigo-700' : 'text-gray-700'}`}>
                                        {opt.label}
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                );

            case 'slider': {
                const val = sliderVal[currentId] ?? (answers[currentId] as number) ?? question.min ?? 0;
                return (
                    <div className="space-y-4">
                        <div className="text-center">
                            <span className="text-5xl font-black text-indigo-600">{val}</span>
                            <span className="text-2xl text-gray-400 ml-2">{question.unit}</span>
                        </div>
                        <input
                            type="range"
                            min={question.min}
                            max={question.max}
                            step={question.step}
                            value={val}
                            onChange={e => {
                                const n = parseInt(e.target.value);
                                setSliderVal(prev => ({ ...prev, [currentId]: n }));
                                setAnswers(prev => ({ ...prev, [currentId]: n }));
                            }}
                            className="w-full h-3 rounded-full appearance-none cursor-pointer accent-indigo-600"
                        />
                        <div className="flex justify-between text-sm text-gray-400">
                            <span>{question.min} {question.unit}</span>
                            <span>{question.max} {question.unit}</span>
                        </div>
                    </div>
                );
            }

            default:
                return null;
        }
    };

    // ── Summary before launching ─────────────────────────────────────────────────

    const SummaryBadges = () => {
        const badges: Array<{ label: string; icon: string }> = [];
        if (context.origin) badges.push({ icon: '📍', label: context.origin });
        if (context.travel_start) badges.push({ icon: '📅', label: `${context.travel_start} → ${context.travel_end}` });
        if (context.traveling_with) badges.push({ icon: '👥', label: context.traveling_with });
        if (context.budget_level) badges.push({ icon: '💰', label: context.budget_level });
        if (context.weather_preference) badges.push({ icon: '🌤️', label: context.weather_preference });
        if ((context.interests?.length ?? 0) > 0) badges.push({ icon: '🎯', label: `${context.interests?.length} interests` });

        if (badges.length === 0) return null;
        return (
            <div className="flex flex-wrap gap-2 justify-center mt-3">
                {badges.map(b => (
                    <span key={b.label} className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-semibold">
                        {b.icon} {b.label}
                    </span>
                ))}
            </div>
        );
    };

    // ── Main render ───────────────────────────────────────────────────────────────

    return (
        <div className="w-full max-w-xl mx-auto select-none">

            {/* Progress bar */}
            <div className="mb-6">
                <div className="flex justify-between text-xs font-semibold text-gray-400 mb-2 uppercase tracking-widest">
                    <span>Question {currentIndex + 1} of {questionQueue.length}</span>
                    <span>{progress}%</span>
                </div>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                    <motion.div
                        className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                        initial={false}
                        animate={{ width: `${progress}%` }}
                        transition={{ duration: 0.4 }}
                    />
                </div>
                {/* Dot indicators for nearby questions */}
                <div className="flex justify-center gap-1.5 mt-3">
                    {questionQueue.slice(0, Math.min(questionQueue.length, 14)).map((_, i) => (
                        <div
                            key={i}
                            className={`rounded-full transition-all duration-300 ${i === currentIndex % 14
                                    ? 'w-4 h-2 bg-indigo-500'
                                    : i < currentIndex % 14
                                        ? 'w-2 h-2 bg-indigo-300'
                                        : 'w-2 h-2 bg-gray-200'
                                }`}
                        />
                    ))}
                </div>
            </div>

            {/* Question card */}
            <AnimatePresence mode="wait">
                <motion.div
                    key={currentId}
                    initial={{ opacity: 0, x: direction === 'fwd' ? 60 : -60 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: direction === 'fwd' ? -60 : 60 }}
                    transition={{ duration: 0.28, ease: 'easeOut' }}
                    className="bg-white rounded-3xl shadow-xl border border-gray-100 p-7 md:p-9"
                >
                    {/* Branching indicator */}
                    {injectedIds.has(currentId) && (
                        <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-50 border border-amber-200 rounded-full text-xs font-semibold text-amber-700 mb-4">
                            <span>✨</span> Follow-up based on your answers
                        </div>
                    )}

                    <h2 className="text-xl md:text-2xl font-bold text-gray-900 mb-1 leading-snug">
                        {question.text}
                    </h2>
                    {question.subtext && (
                        <p className="text-sm text-gray-500 mb-6">{question.subtext}</p>
                    )}
                    {!question.subtext && <div className="mb-5" />}

                    {renderQuestionContent()}

                    {/* Multi-choice tally */}
                    {question.type === 'multi-choice' && (
                        <div className="mt-4 text-center text-xs text-indigo-600 font-medium">
                            {((answers[currentId] as string[]) || []).length} selected
                        </div>
                    )}
                </motion.div>
            </AnimatePresence>

            {/* Context summary badges */}
            <SummaryBadges />

            {/* Navigation */}
            <div className="flex items-center justify-between mt-6 gap-3">
                <button
                    onClick={currentIndex === 0 ? onCancel : goPrev}
                    className="px-5 py-3 text-gray-500 font-semibold hover:text-gray-800 transition-colors text-sm"
                >
                    {currentIndex === 0 ? '✕ Cancel' : '← Back'}
                </button>

                <div className="flex items-center gap-2">
                    {!question.required && !isLast && (
                        <button
                            onClick={skip}
                            className="px-4 py-3 text-gray-400 hover:text-gray-600 font-medium text-sm transition-colors"
                        >
                            Skip
                        </button>
                    )}

                    {isLast ? (
                        <button
                            onClick={handleFinish}
                            className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white
                         font-bold rounded-2xl shadow-lg hover:shadow-xl hover:scale-[1.02]
                         active:scale-[0.98] transition-all text-sm flex items-center gap-2"
                        >
                            🚀 Search Destinations
                        </button>
                    ) : (
                        <button
                            onClick={goNext}
                            disabled={!canAdvance()}
                            className={`px-8 py-3 font-bold rounded-2xl text-sm transition-all shadow-md
                ${canAdvance()
                                    ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white hover:shadow-lg hover:scale-[1.02] active:scale-[0.98]'
                                    : 'bg-gray-100 text-gray-400 cursor-not-allowed shadow-none'
                                }`}
                        >
                            Continue →
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
