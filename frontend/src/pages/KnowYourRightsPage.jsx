import React, { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../components/ui/accordion';
import { rightsAPI } from '../lib/api';
import { 
  Shield, VolumeX, Scale, Megaphone, Users, 
  AlertTriangle, CheckCircle, BookOpen, ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';

const iconMap = {
  'Shield': Shield,
  'VolumeX': VolumeX,
  'Scale': Scale,
  'Megaphone': Megaphone,
  'Users': Users
};

export default function KnowYourRightsPage() {
  const [rights, setRights] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRights();
  }, []);

  const fetchRights = async () => {
    try {
      const response = await rightsAPI.getAll();
      setRights(response.data.rights);
    } catch (error) {
      toast.error('Failed to load rights information');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-8" data-testid="know-your-rights-page">
        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center p-4 rounded-full bg-primary/10 mb-4">
            <BookOpen className="h-8 w-8 text-primary" />
          </div>
          <h1 className="font-serif text-4xl font-bold mb-3">Know Your Rights</h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Understanding your constitutional rights is your first line of defense. 
            These protections apply during any interaction with law enforcement.
          </p>
        </div>

        {/* Emergency Reminder */}
        <Card className="border-yellow-500/20 bg-yellow-500/5">
          <CardContent className="p-6 flex items-start gap-4">
            <AlertTriangle className="h-6 w-6 text-yellow-500 flex-shrink-0 mt-1" />
            <div>
              <h3 className="font-bold text-yellow-600 dark:text-yellow-400 mb-2">
                Important: Stay Safe First
              </h3>
              <p className="text-sm text-muted-foreground">
                While you have these rights, your safety is paramount. Remain calm, keep your hands visible, 
                and avoid sudden movements. You can assert your rights while being cooperative.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Rights Cards */}
        <div className="grid gap-6">
          {rights.map((right, index) => {
            const Icon = iconMap[right.icon] || Shield;
            
            return (
              <Card key={right.id} data-testid={`right-card-${right.id}`}>
                <CardHeader className="pb-4">
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-lg bg-primary/10">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <Badge className="bg-primary/10 text-primary border-primary/20 font-serif">
                          {right.amendment} Amendment
                        </Badge>
                      </div>
                      <CardTitle className="font-serif text-xl">{right.title}</CardTitle>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-muted-foreground">{right.summary}</p>

                  {/* Key Points */}
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm uppercase text-muted-foreground">Key Points</h4>
                    <ul className="space-y-2">
                      {right.key_points.map((point, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0 mt-1" />
                          <span className="text-sm">{point}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* What to Say */}
                  <div className="p-4 rounded-lg bg-muted">
                    <h4 className="font-medium text-sm uppercase text-muted-foreground mb-2">What to Say</h4>
                    <p className="font-serif text-lg italic">"{right.what_to_say}"</p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Additional Tips */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif">General Guidelines During Police Encounters</CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="calm">
                <AccordionTrigger>Stay Calm and Composed</AccordionTrigger>
                <AccordionContent>
                  Keep your hands visible at all times. Avoid making sudden movements. 
                  Speak clearly and politely. Your demeanor can significantly affect the outcome of an encounter.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="record">
                <AccordionTrigger>You Can Record Police</AccordionTrigger>
                <AccordionContent>
                  You have the right to record police officers performing their duties in public spaces. 
                  However, do not interfere with their activities. Police cannot delete your recordings 
                  without a warrant.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="consent">
                <AccordionTrigger>Never Consent to Searches</AccordionTrigger>
                <AccordionContent>
                  You have the right to refuse consent to searches. If police ask to search you, your car, 
                  or your home, you can politely decline by saying "I do not consent to searches." 
                  If they search anyway, do not resist but note the incident.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="ask">
                <AccordionTrigger>Ask If You're Free to Leave</AccordionTrigger>
                <AccordionContent>
                  You can ask "Am I free to leave?" If the answer is yes, calmly walk away. 
                  If you're being detained, you have the right to know why. If you're being arrested, 
                  you have the right to know the charges.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="document">
                <AccordionTrigger>Document Everything</AccordionTrigger>
                <AccordionContent>
                  After the encounter, write down everything you remember: officer names and badge numbers, 
                  patrol car numbers, the agency, location, time, and any witnesses. 
                  Upload evidence to JUSTICE as soon as possible.
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </CardContent>
        </Card>

        {/* CTA */}
        <Card className="bg-primary text-primary-foreground">
          <CardContent className="p-6 text-center">
            <h3 className="font-serif text-2xl font-bold mb-2">Need Real-Time Help?</h3>
            <p className="mb-4 opacity-90">
              Our AI Attorney is available 24/7 to help you understand your rights in any situation.
            </p>
            <a href="/ai-attorney" className="inline-flex items-center gap-2 font-medium hover:underline">
              Talk to AI Attorney <ChevronRight className="h-4 w-4" />
            </a>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
