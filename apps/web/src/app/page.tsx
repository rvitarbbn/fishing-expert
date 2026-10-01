import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="container mx-auto px-4 py-8 max-w-2xl">
      <header className="text-center mb-8">
        <h1 className="text-3xl md:text-4xl font-bold text-primary-800 mb-2">
          יועץ דיג ז׳ירז׳ור
        </h1>
        <p className="text-lg text-gray-600">
          המלצות דמויים לדיג חופי בים התיכון
        </p>
      </header>

      <div className="card mb-6">
        <h2 className="text-xl font-semibold mb-4">בחר מצב</h2>
        <div className="space-y-3">
          <Link
            href="/wizard"
            className="block w-full btn-primary text-center text-lg py-3"
          >
            אשף המלצות
          </Link>
          <Link
            href="/quick"
            className="block w-full btn-secondary text-center"
          >
            מצב מהיר
          </Link>
        </div>
      </div>

      <div className="card bg-blue-50 border border-blue-200">
        <h3 className="font-semibold text-blue-800 mb-2">שים לב</h3>
        <p className="text-sm text-blue-700">
          ההמלצה היא כלי עזר ואינה מבטיחה תפיסה. יש להתאים את הדמוי למגבלות
          החכה והציוד, לבדוק את מצב הים בפועל, ולפעול לפי אזהרות רשמיות ותקנות
          הדיג העדכניות.
        </p>
        <a
          href="https://ims.gov.il/en/meditSea"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block mt-2 text-sm text-blue-600 hover:underline"
        >
          תחזית ימית רשמית - השירות המטאורולוגי
        </a>
      </div>
    </main>
  );
}
