'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { getRecommendation } from '@/lib/api';
import type { LureRecommendation, AlternativeRecommendation } from '@/types/api';

function getSuitabilityClass(score: number): string {
  if (score >= 70) return 'suitability-high';
  if (score >= 40) return 'suitability-medium';
  return 'suitability-low';
}

function getSuitabilityLabel(score: number): string {
  if (score >= 70) return 'התאמה גבוהה';
  if (score >= 40) return 'התאמה בינונית';
  return 'התאמה נמוכה';
}

function LureCard({
  lure,
  isPrimary = false,
  switchCondition,
}: {
  lure: LureRecommendation;
  isPrimary?: boolean;
  switchCondition?: string;
}) {
  return (
    <div className={`card ${isPrimary ? 'border-2 border-primary-500' : 'border border-gray-200'}`}>
      {isPrimary && (
        <div className="text-xs font-medium text-primary-600 mb-2">המלצה ראשית</div>
      )}
      
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="text-xl font-bold">{lure.lure_name_he}</h3>
          <p className="text-sm text-gray-500 ltr-text">{lure.lure_type}</p>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-medium border ${getSuitabilityClass(lure.suitability_score)}`}>
          {getSuitabilityLabel(lure.suitability_score)}
          <span className="mr-1 ltr-nums">({lure.suitability_score})</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm mb-4">
        <div>
          <span className="text-gray-500">אורך:</span>
          <span className="mr-1 ltr-nums">{lure.length_cm_range[0]}-{lure.length_cm_range[1]} ס״מ</span>
        </div>
        <div>
          <span className="text-gray-500">משקל מומלץ:</span>
          <span className="mr-1 ltr-nums font-medium">{lure.recommended_weight_g}g</span>
        </div>
        <div>
          <span className="text-gray-500">צבע:</span>
          <span className="mr-1">{lure.color_family}</span>
        </div>
        <div>
          <span className="text-gray-500">שכבה:</span>
          <span className="mr-1">{lure.working_layer}</span>
        </div>
      </div>

      <div className="mb-4">
        <h4 className="font-medium mb-2">שיטת עבודה</h4>
        <ol className="list-decimal list-inside space-y-1 text-sm">
          {lure.retrieve_steps_he.map((step, i) => (
            <li key={i}>{step}</li>
          ))}
        </ol>
      </div>

      {switchCondition && (
        <div className="text-sm bg-gray-50 p-2 rounded">
          <span className="text-gray-500">מתי לעבור:</span> {switchCondition}
        </div>
      )}
    </div>
  );
}

export default function ResultPage({ params }: { params: { id: string } }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['recommendation', params.id],
    queryFn: () => getRecommendation(params.id),
  });

  if (isLoading) {
    return (
      <main className="container mx-auto px-4 py-8 max-w-2xl">
        <div className="card text-center">
          <p>טוען המלצה...</p>
        </div>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="container mx-auto px-4 py-8 max-w-2xl">
        <div className="card bg-red-50 border border-red-200">
          <p className="text-red-700">שגיאה בטעינת ההמלצה</p>
          <Link href="/" className="btn-primary mt-4 inline-block">
            חזרה להתחלה
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="container mx-auto px-4 py-8 max-w-2xl">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-primary-800">ההמלצה שלך</h1>
        <p className="text-sm text-gray-500">
          {data.normalized_conditions.target_fish as string} | {data.normalized_conditions.time_bucket as string}
        </p>
      </header>

      {/* Warnings */}
      {data.warnings.length > 0 && (
        <div className="card bg-yellow-50 border border-yellow-300 mb-4">
          <h3 className="font-semibold text-yellow-800 mb-2">שים לב</h3>
          <ul className="text-sm text-yellow-700 space-y-1">
            {data.warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Primary recommendation */}
      <div className="mb-4">
        <LureCard lure={data.primary} isPrimary />
      </div>

      {/* Reasons */}
      <div className="card mb-4">
        <h3 className="font-semibold mb-2">למה?</h3>
        <div className="flex flex-wrap gap-2">
          {data.reasons.map((reason, i) => (
            <span key={i} className="px-2 py-1 bg-gray-100 rounded text-sm">
              {reason}
            </span>
          ))}
        </div>
      </div>

      {/* Alternatives */}
      {data.alternatives.length > 0 && (
        <div className="mb-4">
          <h3 className="font-semibold mb-3">חלופות</h3>
          <div className="space-y-3">
            {data.alternatives.map((alt, i) => (
              <LureCard
                key={i}
                lure={alt.recommendation}
                switchCondition={alt.switch_condition_he}
              />
            ))}
          </div>
        </div>
      )}

      {/* Missing information */}
      {data.missing_information.length > 0 && (
        <div className="card bg-blue-50 border border-blue-200 mb-4">
          <h3 className="font-semibold text-blue-800 mb-2">מידע חסר</h3>
          <ul className="text-sm text-blue-700 space-y-1">
            {data.missing_information.map((info, i) => (
              <li key={i}>{info}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Data quality */}
      <div className="card text-sm text-gray-500 mb-4">
        <div className="flex justify-between">
          <span>איכות נתונים:</span>
          <span className="ltr-nums">{Math.round(data.data_quality.completeness_score * 100)}%</span>
        </div>
        <div className="flex justify-between">
          <span>מקור:</span>
          <span>{data.data_quality.data_source}</span>
        </div>
        <div className="flex justify-between">
          <span>גרסת חוקים:</span>
          <span className="ltr-text">{data.rules_version}</span>
        </div>
      </div>

      {/* Expandable rule details */}
      <details className="card mb-4">
        <summary className="cursor-pointer font-medium">איך זה הוחלט?</summary>
        <div className="mt-3 text-sm">
          <p className="text-gray-500 mb-2">חוקים שתרמו לציון:</p>
          <div className="flex flex-wrap gap-1">
            {data.primary.contributing_rule_ids.map((ruleId) => (
              <code key={ruleId} className="px-1 bg-gray-100 rounded text-xs ltr-text">
                {ruleId}
              </code>
            ))}
          </div>
        </div>
      </details>

      {/* IMS link */}
      <div className="text-center mb-6">
        <a
          href="https://ims.gov.il/en/meditSea"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-600 hover:underline"
        >
          אמת תחזית ימית רשמית - השירות המטאורולוגי
        </a>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <Link href="/wizard" className="btn-secondary flex-1 text-center">
          המלצה חדשה
        </Link>
        <Link href="/" className="btn-primary flex-1 text-center">
          חזרה להתחלה
        </Link>
      </div>
    </main>
  );
}
