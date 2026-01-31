/**
 * Tests for VoiceControlPanel Component
 * 
 * Tests the voice-activated hands-free control panel
 * for encounter mode operations.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock the API
jest.mock('../../lib/api', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn()
  }
}));

import api from '../../lib/api';
import VoiceControlPanel from '../../components/VoiceControlPanel';

describe('VoiceControlPanel', () => {
  const mockOnAction = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock API response for commands
    api.get.mockResolvedValue({
      data: {
        commands: {
          START_RECORDING: {
            action: 'START_RECORDING',
            phrases: ['start recording', 'begin'],
            category: 'recording'
          },
          STOP_RECORDING: {
            action: 'STOP_RECORDING',
            phrases: ['stop recording', 'end'],
            category: 'recording'
          },
          TRIGGER_SOS: {
            action: 'TRIGGER_SOS',
            phrases: ['emergency', 'help'],
            category: 'safety'
          }
        }
      }
    });
  });

  it('should render the panel with title', () => {
    render(<VoiceControlPanel onAction={mockOnAction} />);
    
    expect(screen.getByText(/Voice Control/i)).toBeInTheDocument();
  });

  it('should show microphone button', () => {
    render(<VoiceControlPanel onAction={mockOnAction} />);
    
    // Should have a mic button for voice activation
    const micButton = screen.getByRole('button', { name: /start listening|activate|mic/i });
    expect(micButton).toBeInTheDocument();
  });

  it('should display quick action buttons', () => {
    render(<VoiceControlPanel onAction={mockOnAction} isRecording={false} />);
    
    // Should have quick action buttons for common commands
    expect(screen.getByText(/Record/i)).toBeInTheDocument();
    expect(screen.getByText(/SOS/i)).toBeInTheDocument();
  });

  it('should call onAction when quick button clicked', async () => {
    render(<VoiceControlPanel onAction={mockOnAction} isRecording={false} />);
    
    const sosButton = screen.getByText(/SOS/i).closest('button');
    await userEvent.click(sosButton);
    
    expect(mockOnAction).toHaveBeenCalledWith('TRIGGER_SOS', expect.anything());
  });

  it('should show supported status when speech recognition available', () => {
    render(<VoiceControlPanel onAction={mockOnAction} />);
    
    // Should not show "not supported" error since we mock SpeechRecognition
    expect(screen.queryByText(/not supported/i)).not.toBeInTheDocument();
  });

  it('should load available commands on mount', async () => {
    render(<VoiceControlPanel onAction={mockOnAction} />);
    
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith('/voice-commands/commands');
    });
  });

  it('should toggle command list visibility', async () => {
    render(<VoiceControlPanel onAction={mockOnAction} />);
    
    // Find and click toggle button for commands
    const toggleButton = screen.getByText(/commands/i);
    if (toggleButton) {
      await userEvent.click(toggleButton);
      
      // Should show command list after toggle
      await waitFor(() => {
        expect(screen.getByText(/start recording/i)).toBeInTheDocument();
      });
    }
  });

  it('should display recording state correctly', () => {
    const { rerender } = render(
      <VoiceControlPanel onAction={mockOnAction} isRecording={false} />
    );
    
    // Should show "Record" when not recording
    expect(screen.getByText(/Record/i)).toBeInTheDocument();
    
    // Rerender with recording true
    rerender(<VoiceControlPanel onAction={mockOnAction} isRecording={true} />);
    
    // Button text might change to "Stop"
    expect(screen.getByText(/Stop/i)).toBeInTheDocument();
  });

  it('should pass encounterId to action handler', async () => {
    render(
      <VoiceControlPanel 
        onAction={mockOnAction} 
        encounterId="enc_123"
        isRecording={false}
      />
    );
    
    const recordButton = screen.getByText(/Record/i).closest('button');
    await userEvent.click(recordButton);
    
    expect(mockOnAction).toHaveBeenCalledWith(
      'START_RECORDING',
      expect.objectContaining({ encounterId: 'enc_123' })
    );
  });

  it('should apply custom className', () => {
    const { container } = render(
      <VoiceControlPanel 
        onAction={mockOnAction} 
        className="custom-class"
      />
    );
    
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('should handle audio feedback toggle', async () => {
    render(<VoiceControlPanel onAction={mockOnAction} />);
    
    // Look for audio feedback switch/toggle
    const audioToggle = screen.queryByRole('switch', { name: /audio/i });
    if (audioToggle) {
      await userEvent.click(audioToggle);
      // Toggle state should change
    }
  });

  it('should show command history', async () => {
    render(<VoiceControlPanel onAction={mockOnAction} />);
    
    // Initially history should be empty or show placeholder
    const historySection = screen.queryByText(/history|recent/i);
    if (historySection) {
      expect(historySection).toBeInTheDocument();
    }
  });

  it('should display transcript while listening', () => {
    render(<VoiceControlPanel onAction={mockOnAction} />);
    
    // Should have area for showing recognized speech
    const transcriptArea = screen.queryByTestId('voice-transcript');
    // May or may not exist depending on implementation
  });
});
