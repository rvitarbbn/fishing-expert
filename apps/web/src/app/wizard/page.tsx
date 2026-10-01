'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getFishCatalog, createRecommendation } from '@/lib/api';
import type { RecommendationRequest } from '@/types/api';

type WizardStep = 'fish' | 'location' | 'conditions' | 'equipment' | 'review';

const STRUCTURES = [
  { id: 'sandy', name: 'חוף חולי' },
  { id: 'reef', name: 'ריף / סלעי' },
  { id: 'breakwater', name: 'שובר גלים' },
  { id: 'mixed', name: 'מעורב' },
];

const WATER_CLARITY = [
  { id: 'clear', name: 'צלול' },
  { id: 'slightly_murky', name: 'מעט עכור' },
  { id: 'murky', name: 'עכור' },
];

const SEA_STATES = [
  { id: 'flat', name: 'שטוח' },
  { id: 'calm', name: 'רגוע' },
  { id: 'light_chop', name: 'גלים קלים' },
  { id: 'moderate', name: 'בינוני' },
  { id: 'working', name: 'עבודה' },
  { id: 'rough', name: 'סוער' },
];

export default function WizardPage() {
  const router = useRouter();
  const [step, setStep] = useState<WizardStep>('fish');
  const [formData, setFormData] = useState({
    target_fish: '',
    location_name: '',
    structure: '',
    fishing_time: new Date().toISOString().slice(0, 16),
    water_clarity: '',
    sea_state: '',
    foam: false,
    surface_activity: false,
    birds_diving: false,
    rod_cast_min_g: 10,
    rod_cast_max_g: 40,
  });

  const { data: fishCatalog, isLoading: fishLoading } = useQuery({
    queryKey: ['fish-catalog'],
    queryFn: getFishCatalog,
  });

  const recommendMutation = useMutation({
    mutationFn: createRecommendation,
    onSuccess: (data) => {
      router.push(`/result/${data.recommendation_id}`);
    },
  });

  const updateField = (field: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const nextStep = () => {
    const steps: WizardStep[] = ['fish', 'location', 'conditions', 'equipment', 'review'];
    const currentIndex = steps.indexOf(step);
    if (currentIndex < steps.length - 1) {
      setStep(steps[currentIndex + 1]);
    }
  };

  const prevStep = () => {
    const steps: WizardStep[] = ['fish', 'location', 'conditions', 'equipment', 'review'];
    const currentIndex = steps.indexOf(step);
    if (currentIndex > 0) {
      setStep(steps[currentIndex - 1]);
    }
  };

  const handleSubmit = () => {
    const request: RecommendationRequest = {
      target_fish: formData.target_fish || 'unknown',
      fishing_time: new Date(formData.fishing_time).toISOString(),
      location: {
        name: formData.location_name || 'לא צוין',
        structure: formData.structure || null,
      },
      conditions: {
        water_clarity: formData.water_clarity as 'clear' | 'slightly_murky' | 'murky' || null,
        sea_state: formData.sea_state as 'flat' | 'calm' | 'light_chop' | 'moderate' | 'working' | 'rough' || null,
      },
      observations: {
        foam: formData.foam || null,
        surface_activity: formData.surface_activity || null,
        birds_diving: formData.birds_diving || null,
      },
      equipment: {
        rod_cast_min_g: formData.rod_cast_min_g,
        rod_cast_max_g: formData.rod_cast_max_g,
      },
    };

    recommendMutation.mutate(request);
  };

  return (
    <main className="container mx-auto px-4 py-8 max-w-2xl">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-primary-800">אשף המלצות</h1>
        <div className="flex gap-2 mt-4">
          {(['fish', 'location', 'conditions', 'equipment', 'review'] as WizardStep[]).map((s, i) => (
            <div
              key={s}
              className={`h-2 flex-1 rounded ${
                step === s ? 'bg-primary-600' : i < ['fish', 'location', 'conditions', 'equipment', 'review'].indexOf(step) ? 'bg-primary-300' : 'bg-gray-200'
              }`}
            />
          ))}
        </div>
      </header>

      <div className="card">
        {step === 'fish' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">דג מטרה</h2>
            {fishLoading ? (
              <p>טוען...</p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {fishCatalog?.map((fish) => (
                  <button
                    key={fish.id}
                    onClick={() => updateField('target_fish', fish.id)}
                    className={`p-3 rounded-lg border text-right ${
                      formData.target_fish === fish.id
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-medium">{fish.name_he}</div>
                    <div className="text-sm text-gray-500 ltr-text">{fish.name_en}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 'location' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">מיקום וזמן</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">שם המיקום</label>
                <input
                  type="text"
                  value={formData.location_name}
                  onChange={(e) => updateField('location_name', e.target.value)}
                  placeholder="לדוגמה: פלמחים, הרצליה"
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">סוג מבנה</label>
                <div className="grid grid-cols-2 gap-2">
                  {STRUCTURES.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => updateField('structure', s.id)}
                      className={`p-2 rounded-lg border ${
                        formData.structure === s.id
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200'
                      }`}
                    >
                      {s.name}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">זמן דיג</label>
                <input
                  type="datetime-local"
                  value={formData.fishing_time}
                  onChange={(e) => updateField('fishing_time', e.target.value)}
                  className="input-field ltr-text"
                />
              </div>
            </div>
          </div>
        )}

        {step === 'conditions' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">תנאים ותצפיות</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">צלילות מים</label>
                <div className="grid grid-cols-3 gap-2">
                  {WATER_CLARITY.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => updateField('water_clarity', c.id)}
                      className={`p-2 rounded-lg border ${
                        formData.water_clarity === c.id
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200'
                      }`}
                    >
                      {c.name}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">מצב ים</label>
                <div className="grid grid-cols-3 gap-2">
                  {SEA_STATES.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => updateField('sea_state', s.id)}
                      className={`p-2 rounded-lg border text-sm ${
                        formData.sea_state === s.id
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200'
                      }`}
                    >
                      {s.name}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">תצפיות</label>
                <div className="space-y-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.foam}
                      onChange={(e) => updateField('foam', e.target.checked)}
                      className="rounded"
                    />
                    <span>קצף במים</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.surface_activity}
                      onChange={(e) => updateField('surface_activity', e.target.checked)}
                      className="rounded"
                    />
                    <span>פעילות בפני המים</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.birds_diving}
                      onChange={(e) => updateField('birds_diving', e.target.checked)}
                      className="rounded"
                    />
                    <span>ציפורים צוללות</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {step === 'equipment' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">ציוד</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  טווח הטלה של החכה (גרם)
                </label>
                <div className="flex gap-4 items-center">
                  <input
                    type="number"
                    value={formData.rod_cast_min_g}
                    onChange={(e) => updateField('rod_cast_min_g', Number(e.target.value))}
                    min={0}
                    className="input-field w-24 ltr-nums text-center"
                  />
                  <span>עד</span>
                  <input
                    type="number"
                    value={formData.rod_cast_max_g}
                    onChange={(e) => updateField('rod_cast_max_g', Number(e.target.value))}
                    min={1}
                    className="input-field w-24 ltr-nums text-center"
                  />
                </div>
              </div>
              <p className="text-sm text-gray-500">
                טווח ההטלה מופיע על החכה. לדוגמה: 10-40g
              </p>
            </div>
          </div>
        )}

        {step === 'review' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">סיכום</h2>
            <div className="space-y-2 text-sm">
              <p><strong>דג מטרה:</strong> {formData.target_fish || 'לא ידוע'}</p>
              <p><strong>מיקום:</strong> {formData.location_name || 'לא צוין'}</p>
              <p><strong>מבנה:</strong> {STRUCTURES.find(s => s.id === formData.structure)?.name || 'לא צוין'}</p>
              <p><strong>צלילות:</strong> {WATER_CLARITY.find(c => c.id === formData.water_clarity)?.name || 'לא צוין'}</p>
              <p><strong>מצב ים:</strong> {SEA_STATES.find(s => s.id === formData.sea_state)?.name || 'לא צוין'}</p>
              <p><strong>חכה:</strong> <span className="ltr-nums">{formData.rod_cast_min_g}-{formData.rod_cast_max_g}g</span></p>
            </div>
            {recommendMutation.error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                שגיאה: {(recommendMutation.error as Error).message}
              </div>
            )}
          </div>
        )}

        <div className="flex justify-between mt-6">
          <button
            onClick={prevStep}
            disabled={step === 'fish'}
            className="btn-secondary disabled:opacity-50"
          >
            הקודם
          </button>
          {step === 'review' ? (
            <button
              onClick={handleSubmit}
              disabled={recommendMutation.isPending}
              className="btn-primary"
            >
              {recommendMutation.isPending ? 'מעבד...' : 'קבל המלצה'}
            </button>
          ) : (
            <button onClick={nextStep} className="btn-primary">
              הבא
            </button>
          )}
        </div>
      </div>
    </main>
  );
}
