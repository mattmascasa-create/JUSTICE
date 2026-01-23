import React from 'react';
import { Volume2, VolumeX, Play } from 'lucide-react';
import { Button } from './ui/button';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { getSoundOptions, previewSound, getSoundName } from '../services/notificationSounds';

export default function SoundPicker({ value, onChange, disabled = false }) {
  const soundOptions = getSoundOptions();
  
  const handlePreview = (e) => {
    e.stopPropagation();
    if (value && value !== 'none') {
      previewSound(value);
    }
  };
  
  return (
    <div className="flex items-center gap-2">
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Select sound">
            {value === 'none' ? (
              <span className="flex items-center gap-2">
                <VolumeX className="h-4 w-4" />
                Silent
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Volume2 className="h-4 w-4" />
                {getSoundName(value)}
              </span>
            )}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {Object.entries(soundOptions).map(([categoryKey, category]) => (
            <SelectGroup key={categoryKey}>
              <SelectLabel>{category.label}</SelectLabel>
              {category.sounds.map((sound) => (
                <SelectItem key={sound.id} value={sound.id}>
                  <span className="flex items-center gap-2">
                    {sound.id === 'none' ? (
                      <VolumeX className="h-4 w-4" />
                    ) : (
                      <Volume2 className="h-4 w-4" />
                    )}
                    {sound.name}
                  </span>
                </SelectItem>
              ))}
            </SelectGroup>
          ))}
        </SelectContent>
      </Select>
      
      {value && value !== 'none' && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={handlePreview}
          disabled={disabled}
          className="h-9 w-9"
          title="Preview sound"
        >
          <Play className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
