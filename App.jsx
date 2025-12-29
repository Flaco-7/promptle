import React, { useState, useEffect, useCallback } from 'react';
import { Sparkles, Share2, Info, Trophy, AlertCircle, Delete, CornerDownLeft, Loader2 } from 'lucide-react';

/**
 * PROMPTLE - Jeu de devinettes visuelles par IA
 * Configuration du prototype (mots en dur avant l'intégration Supabase)
 */
const WORD_LENGTH = 6;
const MAX_ATTEMPTS = 6;
const TARGET_WORD = "PROMPT";
const DAILY_IMAGE = "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=800";

const KEYBOARD_ROWS = [
  ['A', 'Z', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
  ['Q', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'M'],
  ['ENTER', 'W', 'X', 'C', 'V', 'B', 'N', 'DELETE']
];

export default function App() {
  // États de l'application
  const [guesses, setGuesses] = useState(Array(MAX_ATTEMPTS).fill(''));
  const [currentGuess, setCurrentGuess] = useState('');
  const [attempts, setAttempts] = useState(0);
  const [gameState, setGameState] = useState('playing'); // 'playing', 'won', 'lost'
  const [message, setMessage] = useState('');
  const [usedLetters, setUsedLetters] = useState({}); // Pour l'état du clavier
  const [isLoading, setIsLoading] = useState(false);

  // Validation d'une tentative
  const submitGuess = useCallback(() => {
    if (gameState !== 'playing') return;

    if (currentGuess.length !== WORD_LENGTH) {
      setMessage("Pas assez de lettres...");
      setTimeout(() => setMessage(''), 2000);
      return;
    }

    const newGuesses = [...guesses];
    newGuesses[attempts] = currentGuess;
    setGuesses(newGuesses);

    // Analyse des lettres pour colorer le clavier
    const newUsedLetters = { ...usedLetters };
    currentGuess.split('').forEach((letter, i) => {
      if (TARGET_WORD[i] === letter) {
        newUsedLetters[letter] = 'correct';
      } else if (TARGET_WORD.includes(letter) && newUsedLetters[letter] !== 'correct') {
        newUsedLetters[letter] = 'present';
      } else if (!TARGET_WORD.includes(letter) && !newUsedLetters[letter]) {
        newUsedLetters[letter] = 'absent';
      }
    });
    setUsedLetters(newUsedLetters);

    // Vérification victoire / défaite
    if (currentGuess === TARGET_WORD) {
      setGameState('won');
      setMessage("Magnifique ! Prompt purifié.");
    } else if (attempts + 1 >= MAX_ATTEMPTS) {
      setGameState('lost');
      setMessage(`Le mot secret était : ${TARGET_WORD}`);
    } else {
      setAttempts(prev => prev + 1);
      setCurrentGuess('');
    }
  }, [currentGuess, attempts, gameState, guesses, usedLetters]);

  // Gestion des entrées (clavier physique et virtuel)
  const handleInput = useCallback((key) => {
    if (gameState !== 'playing') return;

    if (key === 'ENTER') {
      submitGuess();
    } else if (key === 'DELETE' || key === 'Backspace') {
      setCurrentGuess(prev => prev.slice(0, -1));
    } else if (/^[a-zA-Z]$/.test(key) && currentGuess.length < WORD_LENGTH) {
      setCurrentGuess(prev => (prev + key).toUpperCase());
    }
  }, [currentGuess, gameState, submitGuess]);

  // Écouteur clavier physique
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey || e.metaKey) return;
      handleInput(e.key === 'Enter' ? 'ENTER' : e.key === 'Backspace' ? 'DELETE' : e.key);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleInput]);

  // Helpers de style
  const getLetterStyle = (guess, index, isCurrentRow) => {
    if (isCurrentRow) {
      return currentGuess[index]
        ? "border-slate-500 bg-slate-800 text-white scale-105"
        : "border-slate-800 bg-slate-900/40 text-transparent";
    }

    if (!guess) return "border-slate-800 bg-slate-900/40 text-transparent";

    const letter = guess[index];
    if (TARGET_WORD[index] === letter) {
      return "bg-violet-600 border-violet-400 text-white shadow-[0_0_15px_rgba(139,92,246,0.3)]";
    }
    if (TARGET_WORD.includes(letter)) {
      return "bg-cyan-600 border-cyan-400 text-white";
    }
    return "bg-slate-800 border-slate-700 text-slate-600 opacity-50";
  };

  const getKeyStyle = (key) => {
    const status = usedLetters[key];
    if (status === 'correct') return "bg-violet-600 text-white shadow-lg shadow-violet-900/20";
    if (status === 'present') return "bg-cyan-600 text-white";
    if (status === 'absent') return "bg-slate-950 text-slate-800 opacity-40";
    return "bg-slate-800 text-slate-200 hover:bg-slate-700";
  };

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 font-sans flex flex-col items-center select-none overflow-x-hidden">
      {/* Barre de navigation */}
      <header className="w-full max-w-lg flex justify-between items-center p-4 md:p-6 border-b border-slate-800/50 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-br from-violet-600 to-cyan-500 p-2 rounded-xl shadow-lg shadow-violet-900/20">
            <Sparkles size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-black tracking-[0.2em] text-white">PROMPTLE</h1>
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest italic">Défi Visuel IA</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400"><Info size={20} /></button>
          <button className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400"><Trophy size={20} /></button>
        </div>
      </header>

      <main className="w-full max-w-md flex-1 flex flex-col gap-4 p-4 mt-2">

        {/* Conteneur de l'image IA floutée */}
        <div className="relative group overflow-hidden rounded-3xl border border-slate-800 bg-slate-900 shadow-2xl">
          <img
            src={DAILY_IMAGE}
            alt="AI Prompt Indice"
            className={`w-full aspect-[4/3] object-cover transition-all duration-1000 ease-in-out ${gameState === 'playing' ? 'blur-2xl grayscale scale-110 saturate-150' : 'blur-none grayscale-0 scale-100'}`}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-80"></div>
          <div className="absolute bottom-4 left-4">
             <span className="bg-slate-900/60 backdrop-blur-md border border-white/10 px-3 py-1 rounded-full text-[10px] text-cyan-300 font-bold tracking-widest uppercase">
               Indice Visuel IA
             </span>
          </div>
        </div>

        {/* Zone de message temporaire */}
        <div className="h-6 flex items-center justify-center">
          {message && (
            <div className="text-[10px] font-black text-violet-400 uppercase tracking-[0.2em] animate-in fade-in slide-in-from-bottom-2">
              {message}
            </div>
          )}
        </div>

        {/* Grille de jeu (Motus Style) */}
        <div className="flex flex-col gap-2 mb-4">
          {guesses.map((guess, i) => (
            <div key={i} className="flex justify-center gap-1.5">
              {Array.from({ length: WORD_LENGTH }).map((_, j) => (
                <div
                  key={j}
                  className={`w-11 h-11 md:w-14 md:h-14 border-2 rounded-xl flex items-center justify-center text-xl font-black transition-all duration-500 ${getLetterStyle(guess, j, i === attempts)}`}
                >
                  {i === attempts ? currentGuess[j] : guess[j]}
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* Clavier virtuel tactile */}
        <div className="mt-auto pb-4 flex flex-col gap-1.5">
          {KEYBOARD_ROWS.map((row, i) => (
            <div key={i} className="flex justify-center gap-1">
              {row.map((key) => {
                const isSpecial = key === 'ENTER' || key === 'DELETE';
                return (
                  <button
                    key={key}
                    onClick={() => handleInput(key)}
                    className={`h-12 flex items-center justify-center rounded-lg font-bold text-[10px] transition-all active:scale-90 shadow-sm ${
                      isSpecial ? 'px-3 bg-slate-700 text-white min-w-[55px]' : `w-8 md:w-10 ${getKeyStyle(key)}`
                    }`}
                  >
                    {key === 'DELETE' ? <Delete size={18} /> : key === 'ENTER' ? <CornerDownLeft size={18} /> : key}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </main>

      {/* Écran de fin de partie */}
      {gameState !== 'playing' && (
        <div className="fixed inset-0 bg-slate-950/95 backdrop-blur-xl flex items-center justify-center p-6 z-50 animate-in fade-in duration-500">
          <div className="bg-slate-900 border border-slate-800 p-8 rounded-[2.5rem] max-w-xs w-full text-center shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-violet-600 to-cyan-500"></div>
            <div className="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <Trophy className={gameState === 'won' ? 'text-yellow-400' : 'text-slate-500'} size={32} />
            </div>
            <h2 className="text-2xl font-black mb-1 uppercase tracking-tighter italic">
              {gameState === 'won' ? 'PRÉDICTION OK' : 'ERREUR SYSTÈME'}
            </h2>
            <p className="text-slate-500 mb-8 text-[11px] font-medium tracking-widest uppercase">
              Mot : <span className="text-white font-bold">{TARGET_WORD}</span>
            </p>
            <button className="w-full py-4 bg-white text-slate-950 rounded-2xl font-black flex items-center justify-center gap-3 hover:bg-slate-200 transition-all active:scale-95 shadow-xl">
              <Share2 size={18} /> PARTAGER MON SCORE
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
