/**
 * EncounterTypeSelector Component
 * 
 * Enhanced encounter type selector with:
 * - Category-based grouping (Law Enforcement, CPS, Government, etc.)
 * - Visual icons and severity indicators
 * - Context-specific rights reminders
 * - Search/filter functionality
 */

import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { ScrollArea } from '../../components/ui/scroll-area';
import { Button } from '../../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Alert, AlertDescription } from '../../components/ui/alert';
import {
  Search, Shield, Users, Building, Scale, Heart,
  GraduationCap, Briefcase, Home, AlertTriangle, Receipt,
  ChevronRight, Info, CheckCircle
} from 'lucide-react';
import {
  encounterCategories,
  universalEncounterTypes,
  getEncounterTypesByCategory,
  getRightsReminders,
  getKeyQuestions,
  getSeverityColor
} from '../../config/encounterTypes';

// Icon mapping for categories
const categoryIcons = {
  law_enforcement: Shield,
  child_family: Users,
  government: Building,
  legal: Scale,
  medical: Heart,
  education: GraduationCap,
  workplace: Briefcase,
  housing: Home,
  accidents: AlertTriangle,
  consumer: Receipt
};

// Color mapping for categories
const categoryColors = {
  law_enforcement: 'text-red-500 bg-red-500/10 border-red-500/30',
  child_family: 'text-purple-500 bg-purple-500/10 border-purple-500/30',
  government: 'text-blue-500 bg-blue-500/10 border-blue-500/30',
  legal: 'text-amber-500 bg-amber-500/10 border-amber-500/30',
  medical: 'text-green-500 bg-green-500/10 border-green-500/30',
  education: 'text-indigo-500 bg-indigo-500/10 border-indigo-500/30',
  workplace: 'text-orange-500 bg-orange-500/10 border-orange-500/30',
  housing: 'text-teal-500 bg-teal-500/10 border-teal-500/30',
  accidents: 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30',
  consumer: 'text-slate-500 bg-slate-500/10 border-slate-500/30'
};

export function EncounterTypeSelector({
  selectedType,
  onSelectType,
  showRightsPreview = true,
  compact = false
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');

  // Filter encounter types based on search and category
  const filteredTypes = useMemo(() => {
    let types = universalEncounterTypes;

    // Filter by category
    if (activeCategory !== 'all') {
      types = types.filter(t => t.category === activeCategory);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      types = types.filter(t =>
        t.label.toLowerCase().includes(query) ||
        t.description.toLowerCase().includes(query)
      );
    }

    return types;
  }, [searchQuery, activeCategory]);

  // Get the selected type details
  const selectedTypeDetails = useMemo(() => {
    return universalEncounterTypes.find(t => t.value === selectedType);
  }, [selectedType]);

  // Get rights reminders for selected type
  const rightsReminders = useMemo(() => {
    if (!selectedType) return [];
    return getRightsReminders(selectedType);
  }, [selectedType]);

  // Get key questions for selected type
  const keyQuestions = useMemo(() => {
    if (!selectedType) return [];
    return getKeyQuestions(selectedType);
  }, [selectedType]);

  // Compact mode - just a dropdown-like list
  if (compact) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Type of Encounter</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search encounter types..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          <ScrollArea className="h-[200px]">
            <div className="space-y-1">
              {filteredTypes.map((type) => {
                const isSelected = selectedType === type.value;
                return (
                  <button
                    key={type.value}
                    onClick={() => onSelectType(type.value)}
                    className={`w-full flex items-center gap-3 p-2 rounded-lg text-left transition-all ${
                      isSelected
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-muted'
                    }`}
                  >
                    <span className="text-lg">{type.icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">{type.label}</p>
                    </div>
                    {isSelected && <CheckCircle className="h-4 w-4 flex-shrink-0" />}
                  </button>
                );
              })}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    );
  }

  // Full mode - with categories and rights preview
  return (
    <div className="space-y-4" data-testid="encounter-type-selector">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search all encounter types..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
          data-testid="encounter-search"
        />
      </div>

      {/* Category Tabs */}
      <Tabs value={activeCategory} onValueChange={setActiveCategory}>
        <ScrollArea className="w-full">
          <TabsList className="inline-flex w-max p-1">
            <TabsTrigger value="all" className="text-xs">
              All Types
            </TabsTrigger>
            {encounterCategories.map((cat) => {
              const Icon = categoryIcons[cat.id] || Shield;
              return (
                <TabsTrigger
                  key={cat.id}
                  value={cat.id}
                  className="text-xs flex items-center gap-1"
                >
                  <Icon className="h-3 w-3" />
                  {cat.label}
                </TabsTrigger>
              );
            })}
          </TabsList>
        </ScrollArea>

        {/* All Categories View */}
        <TabsContent value="all" className="mt-4">
          <Card>
            <CardContent className="p-4">
              <ScrollArea className="h-[300px]">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {filteredTypes.map((type) => (
                    <EncounterTypeCard
                      key={type.value}
                      type={type}
                      isSelected={selectedType === type.value}
                      onClick={() => onSelectType(type.value)}
                    />
                  ))}
                </div>
                {filteredTypes.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No encounter types match your search</p>
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Category-specific Views */}
        {encounterCategories.map((cat) => (
          <TabsContent key={cat.id} value={cat.id} className="mt-4">
            <Card className={`border-2 ${categoryColors[cat.id]}`}>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  {React.createElement(categoryIcons[cat.id] || Shield, {
                    className: `h-5 w-5 ${categoryColors[cat.id].split(' ')[0]}`
                  })}
                  <CardTitle className="text-lg">{cat.label}</CardTitle>
                </div>
                <p className="text-sm text-muted-foreground">{cat.description}</p>
              </CardHeader>
              <CardContent className="pt-2">
                <ScrollArea className="h-[250px]">
                  <div className="space-y-2">
                    {getEncounterTypesByCategory(cat.id).map((type) => (
                      <EncounterTypeCard
                        key={type.value}
                        type={type}
                        isSelected={selectedType === type.value}
                        onClick={() => onSelectType(type.value)}
                      />
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>

      {/* Rights Preview */}
      {showRightsPreview && selectedTypeDetails && (
        <Card className="border-2 border-primary/30 bg-primary/5">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{selectedTypeDetails.icon}</span>
                <div>
                  <CardTitle className="text-lg">{selectedTypeDetails.label}</CardTitle>
                  <p className="text-sm text-muted-foreground">{selectedTypeDetails.description}</p>
                </div>
              </div>
              <Badge className={getSeverityColor(selectedTypeDetails.severity)}>
                {selectedTypeDetails.severity}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Key Questions */}
            {keyQuestions.length > 0 && (
              <div>
                <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                  <Info className="h-4 w-4 text-blue-500" />
                  Key Questions to Ask
                </h4>
                <div className="space-y-1">
                  {keyQuestions.map((q, i) => (
                    <p key={i} className="text-sm bg-blue-500/10 p-2 rounded border border-blue-500/20">
                      "{q}"
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* Rights Reminders Preview */}
            <div>
              <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                <Shield className="h-4 w-4 text-green-500" />
                Your Rights
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {rightsReminders.slice(0, 4).map((right, i) => (
                  <Alert key={i} className="py-2">
                    <AlertDescription className="text-xs">
                      {right}
                    </AlertDescription>
                  </Alert>
                ))}
              </div>
              {rightsReminders.length > 4 && (
                <p className="text-xs text-muted-foreground mt-2 text-center">
                  +{rightsReminders.length - 4} more rights reminders will display during recording
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// Individual encounter type card
function EncounterTypeCard({ type, isSelected, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left transition-all ${
        isSelected
          ? 'bg-primary text-primary-foreground border-primary'
          : `hover:bg-muted ${getSeverityColor(type.severity)}`
      }`}
      data-testid={`encounter-type-${type.value}`}
    >
      <span className="text-xl flex-shrink-0">{type.icon}</span>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm">{type.label}</p>
        <p className={`text-xs truncate ${isSelected ? 'opacity-80' : 'text-muted-foreground'}`}>
          {type.description}
        </p>
      </div>
      {isSelected ? (
        <CheckCircle className="h-5 w-5 flex-shrink-0" />
      ) : (
        <ChevronRight className="h-4 w-4 flex-shrink-0 opacity-50" />
      )}
    </button>
  );
}

export default EncounterTypeSelector;
