import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { 
  Shield, Scale, Siren, FileText, Bot, Users, 
  ChevronRight, Star, CheckCircle, ArrowRight,
  Moon, Sun, Play
} from 'lucide-react';

const features = [
  {
    icon: Bot,
    title: "AI Attorney",
    description: "Get instant constitutional rights guidance powered by advanced AI. 24/7 availability with 89% accuracy.",
    color: "text-blue-500"
  },
  {
    icon: Siren,
    title: "Emergency SOS",
    description: "One-tap emergency activation with automatic location sharing and attorney notification. Response in under 30 seconds.",
    color: "text-red-500"
  },
  {
    icon: FileText,
    title: "Evidence Management",
    description: "Secure, blockchain-verified evidence storage. Upload videos, audio, images with tamper-proof timestamps.",
    color: "text-green-500"
  },
  {
    icon: Scale,
    title: "Attorney Directory",
    description: "Connect with 17,000+ verified civil rights attorneys. Filter by specialization, location, and availability.",
    color: "text-purple-500"
  },
  {
    icon: Shield,
    title: "Rights Protection",
    description: "Know your constitutional rights. Interactive guides for 1st, 4th, 5th, 6th, 8th, and 14th Amendment protections.",
    color: "text-yellow-500"
  },
  {
    icon: Users,
    title: "Case Management",
    description: "Track and manage your civil rights cases. Document incidents, assign attorneys, monitor progress.",
    color: "text-cyan-500"
  }
];

const stats = [
  { value: "500K+", label: "Officers Tracked" },
  { value: "17K+", label: "Verified Attorneys" },
  { value: "89%", label: "AI Accuracy" },
  { value: "<30s", label: "SOS Response" }
];

const testimonials = [
  {
    quote: "JUSTICE helped me understand my rights during a traffic stop. The AI Attorney feature is incredibly helpful.",
    author: "Maria S.",
    role: "Community Advocate"
  },
  {
    quote: "As a civil rights attorney, this platform has revolutionized how I manage cases and connect with clients.",
    author: "David Chen, Esq.",
    role: "Civil Rights Attorney"
  },
  {
    quote: "The evidence management system gave me the documentation I needed to prove my case. Blockchain verification was key.",
    author: "James T.",
    role: "JUSTICE User"
  }
];

export default function LandingPage() {
  const { theme, toggleTheme } = useTheme();
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <Shield className="h-8 w-8" style={{ color: '#3B82F6' }} />
              <span className="font-serif text-xl font-bold">JUSTICE</span>
            </div>
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon" onClick={toggleTheme} data-testid="landing-theme-toggle">
                {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </Button>
              {user ? (
                <Link to="/dashboard">
                  <Button data-testid="go-to-dashboard-btn">Go to Dashboard</Button>
                </Link>
              ) : (
                <>
                  <Link to="/login">
                    <Button variant="ghost" data-testid="landing-login-btn">Sign In</Button>
                  </Link>
                  <Link to="/register">
                    <Button data-testid="landing-get-started-btn">Get Started</Button>
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-4 overflow-hidden">
        <div 
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `url(https://images.unsplash.com/photo-1571909373818-da65ec18d77b?crop=entropy&cs=srgb&fm=jpg&q=85)`,
            backgroundSize: 'cover',
            backgroundPosition: 'center'
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-background via-background/95 to-background" />
        
        <div className="relative max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-signal-blue/10 border border-signal-blue/20 text-signal-blue mb-8" style={{ color: '#3B82F6' }}>
            <Shield className="h-4 w-4" />
            <span className="text-sm font-medium">Protecting Constitutional Rights Since 2024</span>
          </div>
          
          <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6">
            Your Rights.{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-cyan-400">
              Your Protection.
            </span>
            <br />Your Justice.
          </h1>
          
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-10">
            The most comprehensive police accountability platform. AI-powered constitutional rights protection, 
            evidence management, and instant access to civil rights attorneys.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link to="/register">
              <Button size="lg" className="h-14 px-8 text-lg" data-testid="hero-get-protection-btn">
                Get Protection Now
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Button size="lg" variant="outline" className="h-14 px-8 text-lg" data-testid="hero-watch-demo-btn">
              <Play className="mr-2 h-5 w-5" />
              Watch Demo
            </Button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <div key={index} className="text-center">
                <div className="text-3xl sm:text-4xl font-bold mb-1" style={{ color: '#3B82F6' }}>
                  {stat.value}
                </div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 bg-muted/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-serif text-3xl sm:text-4xl font-bold mb-4">
              Complete Rights Protection
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Everything you need to protect your constitutional rights during police encounters.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <Card 
                key={index} 
                className="group hover:shadow-lg transition-all duration-300 border-border hover:border-primary/50"
                data-testid={`feature-card-${index}`}
              >
                <CardContent className="p-6">
                  <div className={`inline-flex p-3 rounded-lg bg-muted mb-4 ${feature.color}`}>
                    <feature.icon className="h-6 w-6" />
                  </div>
                  <h3 className="font-serif text-xl font-bold mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground">{feature.description}</p>
                  <Link to="/register" className="inline-flex items-center mt-4 text-sm font-medium text-primary hover:underline">
                    Learn more <ChevronRight className="h-4 w-4 ml-1" />
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Know Your Rights Preview */}
      <section className="py-20 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="font-serif text-3xl sm:text-4xl font-bold mb-4">
              Know Your Rights
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Essential constitutional amendments that protect you during police encounters.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {[
              { amendment: "4th", title: "Unreasonable Searches", desc: "You can refuse consent to searches" },
              { amendment: "5th", title: "Right to Silence", desc: "You don't have to answer questions" },
              { amendment: "6th", title: "Right to Attorney", desc: "Request a lawyer before questioning" },
              { amendment: "1st", title: "Free Speech", desc: "You can record police in public" }
            ].map((right, index) => (
              <Card key={index} className="border-border">
                <CardContent className="p-6 flex items-start gap-4">
                  <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold font-serif">
                    {right.amendment}
                  </div>
                  <div>
                    <h4 className="font-bold mb-1">{right.title}</h4>
                    <p className="text-sm text-muted-foreground">{right.desc}</p>
                  </div>
                  <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0 ml-auto" />
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="text-center mt-8">
            <Link to="/rights">
              <Button variant="outline" size="lg" data-testid="learn-all-rights-btn">
                Learn All Your Rights
                <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20 px-4 bg-muted/30">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="font-serif text-3xl sm:text-4xl font-bold mb-4">
              Trusted by Thousands
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((testimonial, index) => (
              <Card key={index} className="border-border" data-testid={`testimonial-${index}`}>
                <CardContent className="p-6">
                  <div className="flex gap-1 mb-4">
                    {[1,2,3,4,5].map((star) => (
                      <Star key={star} className="h-4 w-4 fill-yellow-500 text-yellow-500" />
                    ))}
                  </div>
                  <p className="text-muted-foreground mb-4">"{testimonial.quote}"</p>
                  <div>
                    <p className="font-bold">{testimonial.author}</p>
                    <p className="text-sm text-muted-foreground">{testimonial.role}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Emergency CTA */}
      <section className="py-20 px-4 bg-gradient-to-r from-red-600 to-red-700 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <Siren className="h-16 w-16 mx-auto mb-6 animate-pulse" />
          <h2 className="font-serif text-3xl sm:text-4xl font-bold mb-4">
            In an Emergency?
          </h2>
          <p className="text-lg text-white/80 mb-8 max-w-2xl mx-auto">
            Activate SOS with one tap. We'll share your location, start recording, and notify your emergency contacts and nearby attorneys immediately.
          </p>
          <Link to="/register">
            <Button 
              size="lg" 
              className="h-14 px-8 text-lg bg-white text-red-600 hover:bg-white/90"
              data-testid="emergency-signup-btn"
            >
              Sign Up for Free Protection
            </Button>
          </Link>
          <p className="text-sm text-white/60 mt-4">No credit card required. Instant activation.</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 border-t border-border">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <Shield className="h-6 w-6" style={{ color: '#3B82F6' }} />
              <span className="font-serif font-bold">JUSTICE</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <Link to="/rights" className="hover:text-foreground">Know Your Rights</Link>
              <Link to="/attorneys" className="hover:text-foreground">Find an Attorney</Link>
              <a href="#" className="hover:text-foreground">Privacy Policy</a>
              <a href="#" className="hover:text-foreground">Terms of Service</a>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2024 JUSTICE Platform. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
