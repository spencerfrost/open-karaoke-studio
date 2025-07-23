# Upload Workflow Architecture

## Overview

The upload workflow provides a streamlined, multi-step process for adding songs to the karaoke library. It features a stepper-based interface that guides users through song input, metadata enhancement, and audio processing configuration.

## Current Implementation Status

**Primary Files**:
- `frontend/src/components/upload/AddSongStepper.tsx` - Main stepper component
- `frontend/src/components/upload/steps/` - Individual step components
- `frontend/src/hooks/useUploadWorkflow.ts` - Workflow state management
- `frontend/src/types/UploadTypes.ts` - Type definitions

**Status**: ✅ Complete and optimized
**Integration**: Fully integrated with backend processing pipeline

## Core Responsibilities

### Multi-Step User Flow
- **Step 1**: Song input via YouTube URL or manual metadata entry
- **Step 2**: Metadata verification and enhancement with iTunes/YouTube data
- **Step 3**: Processing configuration and audio separation options
- **Step 4**: Upload confirmation and progress tracking

### State Management
- Persistent step progress across user sessions
- Form validation and error handling per step
- Integration with backend upload endpoints
- Real-time processing status updates

### User Experience
- Clear progress indication and navigation
- Comprehensive form validation with helpful error messages
- Responsive design optimized for mobile and desktop
- Accessible keyboard navigation and screen reader support

## Implementation Details

### Component Architecture

```typescript
// Main Stepper Component Structure
export interface AddSongStepperProps {
  onComplete: (songId: string) => void;
  onCancel: () => void;
  initialData?: Partial<UploadFormData>;
}

export const AddSongStepper: React.FC<AddSongStepperProps> = ({
  onComplete,
  onCancel,
  initialData
}) => {
  // Stepper state management
  const { currentStep, formData, errors, isLoading } = useUploadWorkflow();

  // Step component rendering with shared state
  return (
    <StepperContainer>
      <StepIndicator currentStep={currentStep} totalSteps={4} />
      <StepContent step={currentStep} />
      <StepNavigation />
    </StepperContainer>
  );
};
```

### Step Components Pattern

Each step follows a consistent interface pattern:

```typescript
interface StepComponentProps {
  formData: UploadFormData;
  errors: ValidationErrors;
  onNext: (data: Partial<UploadFormData>) => void;
  onPrevious: () => void;
  isLoading: boolean;
}

// Example: Song Input Step
export const SongInputStep: React.FC<StepComponentProps> = ({
  formData,
  errors,
  onNext,
  isLoading
}) => {
  return (
    <form onSubmit={handleSubmit}>
      <YouTubeUrlInput />
      <ManualMetadataForm />
      <StepActions onNext={onNext} />
    </form>
  );
};
```

### Workflow State Management

The upload workflow uses a custom hook that manages:

```typescript
export const useUploadWorkflow = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<UploadFormData>({});
  const [errors, setErrors] = useState<ValidationErrors>({});

  // Step progression logic
  const nextStep = useCallback((data: Partial<UploadFormData>) => {
    // Validate current step
    // Merge form data
    // Advance to next step
  }, [currentStep]);

  // Integration with backend
  const submitUpload = useMutation({
    mutationFn: uploadSong,
    onSuccess: (response) => {
      // Handle successful upload
    },
    onError: (error) => {
      // Handle upload errors
    }
  });

  return { currentStep, formData, errors, nextStep, submitUpload };
};
```

## Integration Points

### Backend API Integration
- **Metadata Enhancement**: Calls to iTunes and YouTube APIs for rich metadata
- **Upload Processing**: File upload with processing configuration
- **Status Tracking**: Real-time updates on processing progress
- **Error Handling**: Comprehensive error reporting from backend services

### Component Integration
- **Library Page**: Direct integration with song library for immediate display
- **Song Details Dialog**: Seamless transition to uploaded song details
- **Player Interface**: Direct access to newly uploaded songs

### State Management Integration
- **Song Store**: Updates global song state on successful upload
- **Upload History**: Tracks recent uploads for user reference
- **Processing Queue**: Integration with background processing status

## Design Patterns

### Stepper Pattern Implementation
- **Progressive Disclosure**: Information revealed step-by-step to reduce cognitive load
- **Validation Gates**: Each step validates before allowing progression
- **Persistent State**: Form data preserved across steps and sessions
- **Error Recovery**: Clear error messaging with guidance for resolution

### Form Handling Strategy
- **Schema Validation**: Using Zod for runtime type checking and validation
- **Conditional Fields**: Dynamic form fields based on previous step selections
- **Auto-save**: Automatic saving of form progress
- **Accessibility**: Full keyboard navigation and screen reader support

### Responsive Design Approach
- **Mobile-First**: Optimized for mobile interaction patterns
- **Progressive Enhancement**: Enhanced features for larger screens
- **Touch-Friendly**: Large touch targets and gesture support
- **Performance**: Optimized for slower network connections

## Dependencies

### External Libraries
- **React Hook Form**: Form state management and validation
- **Zod**: Schema validation and type safety
- **TanStack Query**: API state management and caching
- **Radix UI**: Accessible component primitives

### Internal Dependencies
- **Song Store** (Zustand): Global song state management
- **API Client**: Backend communication layer
- **UI Components**: Shadcn/UI component library
- **Utility Functions**: File handling and validation utilities

### Backend Services
- **Upload Endpoint**: `/api/songs/upload` - File upload and metadata processing
- **Metadata Enhancement**: iTunes and YouTube API integration
- **Processing Status**: Real-time status updates via WebSocket
- **File Storage**: Secure file storage and retrieval

## Performance Considerations

### Upload Optimization
- **Chunked Upload**: Large file upload with progress tracking
- **Background Processing**: Non-blocking audio processing
- **Client-side Validation**: Immediate feedback before server validation
- **Caching Strategy**: Metadata caching to avoid redundant API calls

### User Experience Optimization
- **Progressive Loading**: Loading states for each processing step
- **Error Recovery**: Graceful handling of network interruptions
- **Memory Management**: Efficient handling of large audio files
- **Responsive Feedback**: Immediate visual feedback for user actions

## Error Handling

### Validation Strategy
- **Real-time Validation**: Immediate feedback as users input data
- **Server-side Validation**: Backend validation with detailed error messages
- **Network Error Handling**: Retry logic for network failures
- **File Format Validation**: Client-side file type and size validation

### User-Friendly Error Messages
- **Clear Language**: Non-technical error descriptions
- **Actionable Guidance**: Specific steps to resolve issues
- **Visual Indicators**: Error highlighting with clear visual cues
- **Recovery Options**: Alternative paths when primary flow fails

## Future Enhancements

### Planned Improvements
- **Batch Upload**: Multiple song upload with queue management
- **Advanced Metadata**: Additional metadata sources and manual editing
- **Custom Processing**: User-configurable audio processing options
- **Upload Templates**: Saved upload configurations for repeated use

### Architecture Evolution
- **Modular Steps**: Plugin-based step system for extensibility
- **Workflow Engine**: Generic workflow engine for other multi-step processes
- **Advanced Validation**: ML-powered content validation and suggestions
- **Cloud Integration**: Direct cloud storage upload options

---

**Integration Notes**: The upload workflow serves as a critical entry point for content creation and demonstrates the application's component composition patterns, state management strategies, and backend integration approaches. It showcases the full stack integration between React frontend, Python backend, and external API services.
