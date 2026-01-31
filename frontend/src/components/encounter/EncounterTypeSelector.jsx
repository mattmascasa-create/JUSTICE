/**
 * EncounterTypeSelector Component
 * 
 * A comprehensive selector for all encounter types, organized by category.
 * Supports search, category filtering, and shows relevant information.
 */

import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/tabs';
import {
  Search, Shield, Users, Building, Scale, Heart,
  GraduationCap, Briefcase, Home, AlertTriangle, Receipt,
  ChevronRight, Check, Info
} from 'lucide-react';
import {
  universalEncounterTypes,
  encounterCategories,
  getEncounterTypesByCategory,
  getRightsReminders,
  getKeyQuestions,
  getSeverityColor
} from '../../config/encounterTypes';

// Icon mapping for categories
const categoryIcons = {
  'law_enforcement': Shield,
  'child_family': Users,
  'government': Building,
  'legal': Scale,
  'medical': Heart,
  'education': GraduationCap,
  'workplace': Briefcase,
  'housing': Home,
  'accidents': AlertTriangle,
  'consumer': Receipt
};

// Color mapping for categories
const categoryColors = {
  'law_enforcement': 'text-red-500 bg-red-500/10',
  'child_family': 'text-purple-500 bg-purple-500/10',
  'government': 'text-blue-500 bg-blue-500/10',
  'legal': 'text-amber-500 bg-amber-500/10',
  'medical': 'text-green-500 bg-green-500/10',
  'education': 'text-indigo-500 bg-indigo-500/10',
  'workplace': 'text-orange-500 bg-orange-500/10',
  'housing': 'text-teal-500 bg-teal-500/10',
  'accidents': 'text-yellow-500 bg-yellow-500/10',
  'consumer': 'text-slate-500 bg-slate-500/10'
};

export function EncounterTypeSelector({ 
  value, 
  onChange, 
  showDetails = true,
  compact = false 
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [showInfo, setShowInfo] = useState(false);

  // Filter types based on search and category
  const filteredTypes = useMemo(() => {
    let types = universalEncounterTypes;
    
    if (selectedCategory !== 'all') {
      types = types.filter(t => t.category === selectedCategory);
    }
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      types = types.filter(t => 
        t.label.toLowerCase().includes(query) ||
        t.description.toLowerCase().includes(query) ||
        t.category.toLowerCase().includes(query)
      );
    }
    
    return types;
  }, [searchQuery, selectedCategory]);

  // Get currently selected type
  const selectedType = universalEncounterTypes.find(t => t.value === value);
  const selectedCategoryData = selectedType 
    ? encounterCategories.find(c => c.id === selectedType.category)
    : null;

  // Get rights and questions for selected type
  const rights = selectedType ? getRightsReminders(value) : [];
  const questions = selectedType ? getKeyQuestions(value) : [];

  if (compact) {
    return (
      <div className="space-y-2">
        <Input
          placeholder="Search encounter types..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="mb-2"
        />
        <ScrollArea className="h-64">
          <div className="space-y-1">
            {filteredTypes.map(type => {
              const Icon = categoryIcons[type.category] || AlertTriangle;
              return (
                <button
                  key={type.value}
                  onClick={() => onChange(type.value)}
                  className={`w-full flex items-center gap-3 p-2 rounded-lg text-left transition-all ${
                    value === type.value 
                      ? 'bg-primary/10 border-2 border-primary' 
                      : 'hover:bg-muted border-2 border-transparent'
                  }`}
                >
                  <span className="text-lg">{type.icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{type.label}</p>
                    <p className="text-xs text-muted-foreground truncate">{type.description}</p>
                  </div>
                  {value === type.value && <Check className="h-4 w-4 text-primary" />}
                </button>
              );
            })}
          </div>
        </ScrollArea>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Type of Encounter</CardTitle>
          {selectedType && (
            <Badge className={getSeverityColor(selectedType.severity)}>
              {selectedType.severity.toUpperCase()}
            </Badge>
          )}
        </div>
        
        {/* Search */}
        <div className="relative mt-2">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search all encounter types..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Category Tabs */}
        <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
          <TabsList className="flex flex-wrap h-auto gap-1 bg-transparent p-0">
            <TabsTrigger 
              value="all" 
              className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
            >
              All
            </TabsTrigger>
            {encounterCategories.map(cat => {
              const Icon = categoryIcons[cat.id];
              return (
                <TabsTrigger 
                  key={cat.id} 
                  value={cat.id}
                  className={`data-[state=active]:${categoryColors[cat.id]}`}
                >
                  <Icon className="h-3 w-3 mr-1" />
                  {cat.label}
                </TabsTrigger>
              );
            })}
          </TabsList>
        </Tabs>

        {/* Type List */}
        <ScrollArea className="h-64">
          <div className="grid grid-cols-1 gap-2">
            {filteredTypes.map(type => {
              const Icon = categoryIcons[type.category] || AlertTriangle;
              const isSelected = value === type.value;
              
              return (
                <button
                  key={type.value}
                  onClick={() => onChange(type.value)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-all border-2 ${
                    isSelected 
                      ? 'bg-primary/10 border-primary' 
                      : 'hover:bg-muted border-transparent hover:border-muted-foreground/20'
                  }`}
                  data-testid={`encounter-type-${type.value}`}
                >
                  <div className={`p-2 rounded-lg ${categoryColors[type.category]}`}>
                    <span className="text-xl">{type.icon}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{type.label}</p>
                      <Badge variant="outline" className="text-xs">
                        {encounterCategories.find(c => c.id === type.category)?.label}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{type.description}</p>
                  </div>
                  {isSelected && <Check className="h-5 w-5 text-primary flex-shrink-0" />}
                </button>
              );
            })}
            
            {filteredTypes.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No encounter types found</p>
                <p className="text-sm">Try a different search term</p>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Selected Type Details */}
        {showDetails && selectedType && (
          <div className="pt-4 border-t space-y-4">
            {/* Current Selection */}
            <div className={`p-3 rounded-lg ${categoryColors[selectedType.category]} border`}>
              <div className="flex items-center gap-2">
                <span className="text-2xl">{selectedType.icon}</span>
                <div>
                  <p className="font-bold">{selectedType.label}</p>
                  <p className="text-sm opacity-80">{selectedCategoryData?.label}</p>
                </div>
              </div>
            </div>

            {/* Key Questions to Ask */}
            {questions.length > 0 && (
              <div>
                <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                  <Info className="h-4 w-4" />
                  Key Questions to Ask
                </h4>
                <div className="space-y-1">
                  {questions.map((q, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm">
                      <ChevronRight className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                      <span>{q}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* First Rights Reminder Preview */}
            <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/30">
              <p className="text-sm text-blue-600 dark:text-blue-400 flex items-center gap-2">
                <Shield className="h-4 w-4" />
                {rights[0]}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default EncounterTypeSelector;
