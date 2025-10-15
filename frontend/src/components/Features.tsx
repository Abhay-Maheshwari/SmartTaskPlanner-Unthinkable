import React from 'react';
import { 
  Zap, 
  Brain, 
  Target, 
  BarChart3, 
  Calendar, 
  Users, 
  Shield, 
  Clock,
  CheckCircle,
  TrendingUp,
  Layers,
  Sparkles
} from 'lucide-react';

interface Feature {
  icon: React.ReactNode;
  title: string;
  description: string;
  gradient: string;
  delay: string;
}

const features: Feature[] = [
  {
    icon: <Zap className="w-8 h-8" />,
    title: "AI-Powered Planning",
    description: "Advanced AI breaks down complex goals into actionable tasks with intelligent dependency mapping.",
    gradient: "from-primary to-primary-glow",
    delay: "0ms"
  },
  {
    icon: <Brain className="w-8 h-8" />,
    title: "Smart Automation",
    description: "Automatically adjusts timelines, suggests optimizations, and learns from your workflow patterns.",
    gradient: "from-primary-glow to-accent",
    delay: "100ms"
  },
  {
    icon: <Target className="w-8 h-8" />,
    title: "Goal Tracking",
    description: "Monitor progress toward your main objectives with smart milestone tracking and alerts.",
    gradient: "from-accent to-accent/80",
    delay: "200ms"
  },
  {
    icon: <BarChart3 className="w-8 h-8" />,
    title: "Analytics Dashboard",
    description: "Comprehensive analytics dashboard to track project health, velocity, and completion rates.",
    gradient: "from-accent/80 to-success",
    delay: "300ms"
  },
  {
    icon: <Calendar className="w-8 h-8" />,
    title: "Timeline Management",
    description: "Visual timeline views with drag-and-drop scheduling and deadline management.",
    gradient: "from-success to-success/80",
    delay: "400ms"
  },
  {
    icon: <Users className="w-8 h-8" />,
    title: "Team Collaboration",
    description: "Share plans, assign tasks, and collaborate with your team in real-time.",
    gradient: "from-success/80 to-primary",
    delay: "500ms"
  },
  {
    icon: <Shield className="w-8 h-8" />,
    title: "Secure & Private",
    description: "Enterprise-grade security with end-to-end encryption for all your project data.",
    gradient: "from-primary to-primary-glow",
    delay: "600ms"
  },
  {
    icon: <Clock className="w-8 h-8" />,
    title: "Real-time Updates",
    description: "Get instant notifications and updates as your plan progresses and evolves.",
    gradient: "from-primary-glow to-accent",
    delay: "700ms"
  }
];

export const Features = () => {
  return (
    <section className="py-20 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-mesh opacity-10"></div>
      
      <div className="container mx-auto px-4 relative z-10">
        {/* Section Header */}
        <div className="text-center mb-16 animate-fade-up">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-heading font-bold mb-6 bg-gradient-primary bg-clip-text text-transparent">
            Powerful Features
          </h2>
          <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
            Everything you need to transform ideas into successful projects
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, index) => (
            <div
              key={index}
              className="group relative animate-fade-up hover-3d"
              style={{ animationDelay: feature.delay }}
            >
              {/* Glassmorphic Card */}
              <div className="group relative p-6 bg-card/80 backdrop-blur-sm hover:bg-card/90 transition-all duration-500 hover-magnetic hover:shadow-elevated rounded-2xl border border-border/50 overflow-hidden h-full">
                {/* Gradient Border Effect */}
                <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-20 transition-opacity duration-500 blur-sm`}></div>
                
                {/* Background Pattern */}
                <div className="absolute inset-0 opacity-5 group-hover:opacity-10 transition-opacity duration-500"></div>

                {/* Icon */}
                <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} text-white mb-4 shadow-glow group-hover:scale-110 transition-transform duration-300`}>
                  {feature.icon}
                </div>

                {/* Content */}
                <h3 className="text-lg font-semibold text-card-foreground mb-3 group-hover:text-primary transition-all duration-300">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed group-hover:text-card-foreground/80 transition-colors duration-300">
                  {feature.description}
                </p>

                {/* Hover Glow Effect */}
                <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-500`}></div>
              </div>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
};

