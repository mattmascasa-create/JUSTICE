import React, { useState, useEffect } from 'react';
import { 
  BookOpen, Trophy, Star, ChevronRight, CheckCircle, XCircle,
  Loader2, Award, Flame, Car, Home, Video, Globe, Handshake,
  Footprints, Target, Users, ArrowRight, RotateCcw
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { toast } from 'sonner';
import { trainingAPI } from '../lib/api';
import { cn } from '../lib/utils';

const CATEGORY_ICONS = {
  traffic_stop: Car,
  pedestrian_stop: Footprints,
  home_search: Home,
  recording_rights: Video,
  arrest_procedures: Handshake,
  immigration: Globe
};

const BADGE_ICONS = {
  star: Star,
  car: Car,
  video: Video,
  home: Home,
  trophy: Trophy,
  award: Award,
  'check-circle': CheckCircle,
  flame: Flame
};

export default function RightsTrainingPage() {
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [progress, setProgress] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [allBadges, setAllBadges] = useState([]);
  
  // Scenario state
  const [activeScenario, setActiveScenario] = useState(null);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [answerResult, setAnswerResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  // Active tab and category
  const [activeTab, setActiveTab] = useState('learn');
  const [selectedCategory, setSelectedCategory] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [catRes, scenRes, progRes, badgeRes, leaderRes] = await Promise.all([
        trainingAPI.getCategories(),
        trainingAPI.getScenarios(),
        trainingAPI.getProgress(),
        trainingAPI.getBadges(),
        trainingAPI.getLeaderboard(5)
      ]);
      setCategories(catRes.data.categories || []);
      setScenarios(scenRes.data.scenarios || []);
      setProgress(progRes.data);
      setAllBadges(badgeRes.data.badges || []);
      setLeaderboard(leaderRes.data.leaderboard || []);
    } catch (error) {
      console.error('Error fetching training data:', error);
      toast.error('Failed to load training content');
    } finally {
      setLoading(false);
    }
  };

  const startScenario = (scenario) => {
    setActiveScenario(scenario);
    setSelectedAnswer(null);
    setAnswerResult(null);
  };

  const submitAnswer = async () => {
    if (!selectedAnswer || !activeScenario) return;
    
    setSubmitting(true);
    try {
      const res = await trainingAPI.submitAnswer(activeScenario.id, selectedAnswer);
      setAnswerResult(res.data);
      
      // Refresh progress
      const progRes = await trainingAPI.getProgress();
      setProgress(progRes.data);
      
      if (res.data.correct) {
        toast.success(`+${res.data.points_earned} points!`);
      }
      
      if (res.data.new_badges?.length > 0) {
        res.data.new_badges.forEach(badge => {
          toast.success(`🏆 Badge earned: ${badge.name}!`);
        });
      }
    } catch (error) {
      toast.error('Failed to submit answer');
    } finally {
      setSubmitting(false);
    }
  };

  const nextScenario = () => {
    const categoryScenarios = scenarios.filter(s => s.category === activeScenario?.category);
    const currentIndex = categoryScenarios.findIndex(s => s.id === activeScenario?.id);
    const nextIndex = currentIndex + 1;
    
    if (nextIndex < categoryScenarios.length) {
      startScenario(categoryScenarios[nextIndex]);
    } else {
      setActiveScenario(null);
      toast.success('Category completed!');
    }
  };

  const getCategoryProgress = (categoryId) => {
    const categoryScenarios = scenarios.filter(s => s.category === categoryId);
    const completed = categoryScenarios.filter(s => 
      progress?.completed_scenarios?.includes(s.id)
    ).length;
    return { completed, total: categoryScenarios.length };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6" data-testid="rights-training-page">
      {/* Header with Progress */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <BookOpen className="h-8 w-8 text-primary" />
            Know Your Rights
          </h1>
          <p className="text-muted-foreground">
            Interactive training to protect yourself during police encounters
          </p>
        </div>
        
        {progress && (
          <Card className="w-full md:w-auto">
            <CardContent className="p-4">
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <div className="text-3xl font-bold text-primary">{progress.level}</div>
                  <div className="text-xs text-muted-foreground">Level</div>
                </div>
                <div className="flex-1 min-w-[120px]">
                  <div className="flex justify-between text-xs mb-1">
                    <span>{progress.total_points} pts</span>
                    <span>{progress.next_level_points} pts</span>
                  </div>
                  <Progress 
                    value={(progress.total_points / progress.next_level_points) * 100} 
                    className="h-2"
                  />
                </div>
                <div className="text-center">
                  <div className="text-xl font-bold flex items-center gap-1">
                    <Flame className="h-5 w-5 text-orange-500" />
                    {progress.streak_days || 0}
                  </div>
                  <div className="text-xs text-muted-foreground">Streak</div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="learn">Learn</TabsTrigger>
          <TabsTrigger value="badges">Badges</TabsTrigger>
          <TabsTrigger value="leaderboard">Leaderboard</TabsTrigger>
        </TabsList>

        {/* Learn Tab */}
        <TabsContent value="learn" className="space-y-6">
          {/* Categories Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {categories.map((category) => {
              const Icon = CATEGORY_ICONS[category.id] || BookOpen;
              const { completed, total } = getCategoryProgress(category.id);
              const isComplete = completed === total && total > 0;
              
              return (
                <Card 
                  key={category.id}
                  className={cn(
                    "cursor-pointer hover:border-primary/50 transition-colors",
                    selectedCategory === category.id && "border-primary",
                    isComplete && "bg-green-500/5 border-green-500/30"
                  )}
                  onClick={() => setSelectedCategory(
                    selectedCategory === category.id ? null : category.id
                  )}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <div className={`p-2 rounded-lg bg-${category.color || 'blue'}-500/10`}>
                        <Icon className={`h-6 w-6 text-${category.color || 'blue'}-500`} />
                      </div>
                      {isComplete && (
                        <Badge className="bg-green-500">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Complete
                        </Badge>
                      )}
                    </div>
                    <CardTitle className="text-lg">{category.title}</CardTitle>
                    <CardDescription>{category.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <Progress value={(completed / total) * 100} className="flex-1 mr-4 h-2" />
                      <span className="text-sm text-muted-foreground">{completed}/{total}</span>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Scenarios List */}
          {selectedCategory && (
            <Card>
              <CardHeader>
                <CardTitle>
                  {categories.find(c => c.id === selectedCategory)?.title} Scenarios
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {scenarios
                    .filter(s => s.category === selectedCategory)
                    .map((scenario) => {
                      const isCompleted = progress?.completed_scenarios?.includes(scenario.id);
                      
                      return (
                        <div
                          key={scenario.id}
                          className={cn(
                            "flex items-center justify-between p-4 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors",
                            isCompleted && "bg-green-500/5 border-green-500/20"
                          )}
                          onClick={() => startScenario(scenario)}
                        >
                          <div className="flex items-center gap-3">
                            {isCompleted ? (
                              <CheckCircle className="h-5 w-5 text-green-500" />
                            ) : (
                              <Target className="h-5 w-5 text-muted-foreground" />
                            )}
                            <div>
                              <h4 className="font-medium">{scenario.title}</h4>
                              <div className="flex items-center gap-2 mt-1">
                                <Badge variant="outline" className="text-xs">
                                  {scenario.difficulty}
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  +{scenario.points} pts
                                </span>
                              </div>
                            </div>
                          </div>
                          <ChevronRight className="h-5 w-5 text-muted-foreground" />
                        </div>
                      );
                    })}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Badges Tab */}
        <TabsContent value="badges">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {allBadges.map((badge) => {
              const Icon = BADGE_ICONS[badge.icon] || Star;
              const isEarned = progress?.badges?.includes(badge.id);
              
              return (
                <Card 
                  key={badge.id}
                  className={cn(
                    "transition-all",
                    isEarned ? "border-yellow-500/50 bg-yellow-500/5" : "opacity-60"
                  )}
                >
                  <CardContent className="p-6 text-center">
                    <div className={cn(
                      "w-16 h-16 rounded-full mx-auto mb-3 flex items-center justify-center",
                      isEarned ? "bg-yellow-500/20" : "bg-muted"
                    )}>
                      <Icon className={cn(
                        "h-8 w-8",
                        isEarned ? "text-yellow-500" : "text-muted-foreground"
                      )} />
                    </div>
                    <h3 className="font-semibold">{badge.name}</h3>
                    <p className="text-sm text-muted-foreground mt-1">{badge.description}</p>
                    {isEarned && (
                      <Badge className="mt-2 bg-yellow-500">Earned!</Badge>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        {/* Leaderboard Tab */}
        <TabsContent value="leaderboard">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Trophy className="h-5 w-5 text-yellow-500" />
                Top Learners
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {leaderboard.map((leader, idx) => (
                  <div
                    key={leader.user_id}
                    className={cn(
                      "flex items-center gap-4 p-4 rounded-lg",
                      idx === 0 ? "bg-yellow-500/10 border border-yellow-500/30" :
                      idx === 1 ? "bg-gray-500/10" :
                      idx === 2 ? "bg-orange-500/10" : "bg-muted/50"
                    )}
                  >
                    <div className={cn(
                      "w-10 h-10 rounded-full flex items-center justify-center font-bold",
                      idx === 0 ? "bg-yellow-500 text-white" :
                      idx === 1 ? "bg-gray-400 text-white" :
                      idx === 2 ? "bg-orange-400 text-white" : "bg-muted"
                    )}>
                      {idx + 1}
                    </div>
                    <div className="flex-1">
                      <div className="font-medium">{leader.name}</div>
                      <div className="text-sm text-muted-foreground">
                        Level {leader.level} • {leader.badge_count} badges
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold">{leader.total_points}</div>
                      <div className="text-xs text-muted-foreground">points</div>
                    </div>
                  </div>
                ))}
                {leaderboard.length === 0 && (
                  <p className="text-center text-muted-foreground py-8">
                    No learners yet. Be the first!
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Scenario Dialog */}
      <Dialog open={!!activeScenario} onOpenChange={() => setActiveScenario(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {activeScenario && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{activeScenario.difficulty}</Badge>
                  <Badge>+{activeScenario.points} pts</Badge>
                </div>
                <DialogTitle className="text-xl">{activeScenario.title}</DialogTitle>
                <DialogDescription className="text-base">
                  {activeScenario.situation}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 py-4">
                <h4 className="font-semibold">{activeScenario.question}</h4>
                
                <div className="space-y-2">
                  {activeScenario.options.map((option) => {
                    const isSelected = selectedAnswer === option.id;
                    const showResult = answerResult !== null;
                    const isCorrect = showResult && answerResult.correct_answer?.id === option.id;
                    const isWrong = showResult && isSelected && !answerResult.correct;
                    
                    return (
                      <button
                        key={option.id}
                        onClick={() => !answerResult && setSelectedAnswer(option.id)}
                        disabled={!!answerResult}
                        className={cn(
                          "w-full p-4 rounded-lg border text-left transition-all",
                          !showResult && isSelected && "border-primary bg-primary/5",
                          !showResult && !isSelected && "hover:border-primary/50",
                          isCorrect && "border-green-500 bg-green-500/10",
                          isWrong && "border-red-500 bg-red-500/10"
                        )}
                      >
                        <div className="flex items-start gap-3">
                          <div className={cn(
                            "w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-0.5",
                            isSelected && !showResult && "border-primary bg-primary text-white",
                            isCorrect && "border-green-500 bg-green-500 text-white",
                            isWrong && "border-red-500 bg-red-500 text-white"
                          )}>
                            {isCorrect && <CheckCircle className="h-4 w-4" />}
                            {isWrong && <XCircle className="h-4 w-4" />}
                          </div>
                          <span>{option.text}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Result Section */}
                {answerResult && (
                  <div className={cn(
                    "p-4 rounded-lg",
                    answerResult.correct ? "bg-green-500/10 border border-green-500/30" : "bg-red-500/10 border border-red-500/30"
                  )}>
                    <h4 className={cn(
                      "font-semibold mb-2",
                      answerResult.correct ? "text-green-600" : "text-red-600"
                    )}>
                      {answerResult.correct ? "Correct!" : "Not quite right"}
                      {answerResult.points_earned > 0 && ` +${answerResult.points_earned} points`}
                    </h4>
                    <p className="text-sm mb-3">{answerResult.explanation}</p>
                    
                    {answerResult.key_rights && (
                      <div className="mb-3">
                        <h5 className="font-medium text-sm mb-1">Key Rights:</h5>
                        <ul className="text-sm space-y-1">
                          {answerResult.key_rights.map((right, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <CheckCircle className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                              {right}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {answerResult.tips && (
                      <div>
                        <h5 className="font-medium text-sm mb-1">Tips:</h5>
                        <ul className="text-sm space-y-1">
                          {answerResult.tips.map((tip, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                              {tip}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3">
                {!answerResult ? (
                  <>
                    <Button variant="outline" onClick={() => setActiveScenario(null)}>
                      Cancel
                    </Button>
                    <Button 
                      onClick={submitAnswer}
                      disabled={!selectedAnswer || submitting}
                    >
                      {submitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                      Submit Answer
                    </Button>
                  </>
                ) : (
                  <>
                    <Button variant="outline" onClick={() => {
                      setSelectedAnswer(null);
                      setAnswerResult(null);
                    }}>
                      <RotateCcw className="h-4 w-4 mr-2" />
                      Try Again
                    </Button>
                    <Button onClick={nextScenario}>
                      Next Scenario
                      <ChevronRight className="h-4 w-4 ml-2" />
                    </Button>
                  </>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
