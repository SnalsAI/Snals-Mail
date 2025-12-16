/**
 * WorkflowStepper - Progress indicator per workflow NLP Training
 */

import { Check, ArrowRight } from 'lucide-react'
import type { WorkflowStep, StepValidation } from './types'

interface WorkflowStepperProps {
  currentStep: WorkflowStep
  onStepClick: (step: WorkflowStep) => void
  validation: StepValidation
  selectedEmailCount: number
  approvedSampleCount: number
}

const STEPS: { id: WorkflowStep; label: string; shortLabel: string }[] = [
  { id: 'select', label: 'Seleziona Email', shortLabel: 'Selezione' },
  { id: 'analyze', label: 'Analizza con ChatGPT', shortLabel: 'Analisi' },
  { id: 'approve', label: 'Approva Sample', shortLabel: 'Approvazione' },
  { id: 'benchmark-before', label: 'Benchmark Prima', shortLabel: 'Pre-Test' },
  { id: 'apply', label: 'Applica Training', shortLabel: 'Training' },
  { id: 'benchmark-after', label: 'Benchmark Dopo', shortLabel: 'Post-Test' },
  { id: 'compare', label: 'Confronta Risultati', shortLabel: 'Confronto' }
]

export function WorkflowStepper({
  currentStep,
  onStepClick,
  validation,
  selectedEmailCount,
  approvedSampleCount
}: WorkflowStepperProps) {
  const currentIndex = STEPS.findIndex(s => s.id === currentStep)

  const getStepStatus = (step: WorkflowStep, index: number): 'completed' | 'current' | 'upcoming' | 'optional' => {
    if (index < currentIndex) return 'completed'
    if (index === currentIndex) return 'current'
    if (step === 'benchmark-before' || step === 'benchmark-after') return 'optional'
    return 'upcoming'
  }

  const isStepClickable = (step: WorkflowStep): boolean => {
    switch (step) {
      case 'select':
        return true
      case 'analyze':
        return validation.canProceedToAnalyze
      case 'approve':
        return validation.canProceedToApprove
      case 'benchmark-before':
        return validation.canBenchmark
      case 'apply':
        return validation.canApplyTraining
      case 'benchmark-after':
        return validation.canBenchmark
      case 'compare':
        return true
      default:
        return false
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">Workflow Training</h3>
        <div className="text-sm text-gray-500">
          {selectedEmailCount > 0 && (
            <span className="mr-4">{selectedEmailCount} email selezionate</span>
          )}
          {approvedSampleCount > 0 && (
            <span>{approvedSampleCount} sample approvati</span>
          )}
        </div>
      </div>

      {/* Steps */}
      <div className="flex items-center justify-between">
        {STEPS.map((step, index) => {
          const status = getStepStatus(step.id, index)
          const clickable = isStepClickable(step.id)
          const isOptional = step.id === 'benchmark-before' || step.id === 'benchmark-after'

          return (
            <div key={step.id} className="flex items-center">
              {/* Step indicator */}
              <button
                onClick={() => clickable && onStepClick(step.id)}
                disabled={!clickable}
                className={`
                  flex flex-col items-center group
                  ${clickable ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}
                `}
                title={step.label}
              >
                {/* Circle */}
                <div
                  className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                    transition-colors duration-200
                    ${status === 'completed'
                      ? 'bg-green-500 text-white'
                      : status === 'current'
                        ? 'bg-primary-600 text-white ring-2 ring-primary-300'
                        : isOptional
                          ? 'bg-gray-100 text-gray-400 border-2 border-dashed border-gray-300'
                          : 'bg-gray-200 text-gray-500'
                    }
                    ${clickable && status !== 'current' ? 'group-hover:ring-2 group-hover:ring-gray-300' : ''}
                  `}
                >
                  {status === 'completed' ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </div>

                {/* Label */}
                <span
                  className={`
                    mt-1 text-xs font-medium whitespace-nowrap
                    ${status === 'current' ? 'text-primary-600' : 'text-gray-500'}
                  `}
                >
                  {step.shortLabel}
                  {isOptional && <span className="text-gray-400 ml-1">(opt)</span>}
                </span>
              </button>

              {/* Connector */}
              {index < STEPS.length - 1 && (
                <div className="flex-1 mx-2">
                  <ArrowRight
                    className={`
                      w-4 h-4 mx-auto
                      ${index < currentIndex ? 'text-green-500' : 'text-gray-300'}
                    `}
                  />
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Current step description */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <p className="text-sm text-gray-600">
          {currentStep === 'select' && 'Seleziona le email da analizzare per il training.'}
          {currentStep === 'analyze' && 'Analizza le email con ChatGPT per estrarre entità.'}
          {currentStep === 'approve' && 'Rivedi e approva i sample estratti da ChatGPT.'}
          {currentStep === 'benchmark-before' && 'Esegui un benchmark per misurare le performance attuali.'}
          {currentStep === 'apply' && 'Applica il training per migliorare il modello NLP.'}
          {currentStep === 'benchmark-after' && 'Esegui un benchmark per misurare i miglioramenti.'}
          {currentStep === 'compare' && 'Confronta i risultati prima e dopo il training.'}
        </p>
      </div>
    </div>
  )
}

export default WorkflowStepper
