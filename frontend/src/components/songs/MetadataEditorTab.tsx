import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Music, Save, Upload } from 'lucide-react';
import { Song } from '../../types/Song';
import vintageTheme from '../../utils/theme';

interface MetadataEditorTabProps {
  song: Song;
  onSave: (metadata: Partial<Song>) => void;
}

const MetadataEditorTab: React.FC<MetadataEditorTabProps> = ({ song, onSave }) => {
  const colors = vintageTheme.colors;
  
  const [metadata, setMetadata] = useState<Partial<Song>>({
    title: song.title,
    artist: song.artist,
    album: song.album || '',
    year: song.year || '',
    genre: song.genre || '',
    language: song.language || '',
    coverArt: song.coverArt,
  });

  const handleChange = (field: keyof Song, value: string) => {
    setMetadata(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave(metadata);
  };
  
  return (
    <div className="p-2">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Cover Art Column */}
        <div className="flex flex-col items-center gap-4">
          <div 
            className="w-full aspect-square rounded-md flex items-center justify-center relative overflow-hidden"
            style={{ backgroundColor: `${colors.orangePeel}20` }}
          >
            {metadata.coverArt ? (
              <img
                src={metadata.coverArt}
                alt={metadata.title}
                className="h-full w-full object-cover"
              />
            ) : (
              <Music size={64} style={{ color: colors.darkCyan }} />
            )}
          </div>
          
          <Button 
            variant="outline" 
            className="w-full flex items-center justify-center gap-2"
            style={{
              borderColor: colors.orangePeel,
              color: colors.darkCyan
            }}
          >
            <Upload size={18} />
            Change Image
          </Button>
        </div>
        
        {/* Form Fields Column */}
        <div className="md:col-span-2 space-y-4">
          <div className="space-y-2">
            <Label className="text-card-foreground" htmlFor="title">Title</Label>
            <Input 
              id="title" 
              value={metadata.title}
              onChange={(e) => handleChange('title', e.target.value)}
              className="w-full text-card-foreground"
              style={{
                borderColor: colors.orangePeel,
                backgroundColor: colors.lemonChiffon
              }}
            />
          </div>
          
          <div className="space-y-2">
            <Label className="text-card-foreground" htmlFor="artist">Artist</Label>
            <Input 
              id="artist" 
              value={metadata.artist}
              onChange={(e) => handleChange('artist', e.target.value)}
              className="w-full text-card-foreground"
              style={{
                borderColor: colors.orangePeel,
                backgroundColor: colors.lemonChiffon
              }}
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-card-foreground" htmlFor="album">Album</Label>
              <Input 
                id="album" 
                value={metadata.album}
                onChange={(e) => handleChange('album', e.target.value)}
                className="w-full text-card-foreground"
                style={{
                  borderColor: colors.orangePeel,
                  backgroundColor: colors.lemonChiffon
                }}
              />
            </div>
            
            <div className="space-y-2">
              <Label className="text-card-foreground" htmlFor="year">Year</Label>
              <Input 
                id="year" 
                value={metadata.year}
                onChange={(e) => handleChange('year', e.target.value)}
                className="w-full text-card-foreground"
                style={{
                  borderColor: colors.orangePeel,
                  backgroundColor: colors.lemonChiffon
                }}
              />
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-card-foreground" htmlFor="genre">Genre</Label>
              <Select 
                value={metadata.genre || ''} 
                onValueChange={(value) => handleChange('genre', value)}
              >
                <SelectTrigger 
                  className="w-full text-card-foreground"
                  style={{
                    borderColor: colors.orangePeel,
                    backgroundColor: colors.lemonChiffon
                  }}
                >
                  <SelectValue placeholder="Select genre" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Rock">Rock</SelectItem>
                  <SelectItem value="Pop">Pop</SelectItem>
                  <SelectItem value="R&B">R&B</SelectItem>
                  <SelectItem value="Hip Hop">Hip Hop</SelectItem>
                  <SelectItem value="Country">Country</SelectItem>
                  <SelectItem value="Electronic">Electronic</SelectItem>
                  <SelectItem value="Jazz">Jazz</SelectItem>
                  <SelectItem value="Classical">Classical</SelectItem>
                  <SelectItem value="Folk">Folk</SelectItem>
                  <SelectItem value="Other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label className="text-card-foreground" className="text-card-foreground" htmlFor="language">Language</Label>
              <Select 
                value={metadata.language || ''} 
                onValueChange={(value) => handleChange('language', value)}
              >
                <SelectTrigger 
                  className="w-full text-card-foreground"
                  style={{
                    borderColor: colors.orangePeel,
                    backgroundColor: colors.lemonChiffon
                  }}
                >
                  <SelectValue placeholder="Select language" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="English">English</SelectItem>
                  <SelectItem value="Spanish">Spanish</SelectItem>
                  <SelectItem value="French">French</SelectItem>
                  <SelectItem value="German">German</SelectItem>
                  <SelectItem value="Japanese">Japanese</SelectItem>
                  <SelectItem value="Korean">Korean</SelectItem>
                  <SelectItem value="Chinese">Chinese</SelectItem>
                  <SelectItem value="Italian">Italian</SelectItem>
                  <SelectItem value="Portuguese">Portuguese</SelectItem>
                  <SelectItem value="Other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </div>
      
      <div className="mt-6 flex justify-end">
        <Button 
          className="flex items-center gap-2"
          onClick={handleSave}
          style={{
            backgroundColor: colors.darkCyan,
            color: colors.lemonChiffon
          }}
        >
          <Save size={18} />
          Save Changes
        </Button>
      </div>
    </div>
  );
};

export default MetadataEditorTab;