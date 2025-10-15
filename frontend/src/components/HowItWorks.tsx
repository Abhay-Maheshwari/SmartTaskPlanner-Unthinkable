import { 
  Lightbulb, 
  Brain, 
  BarChart3, 
  Rocket,
  ArrowDown,
  CheckCircle,
  Clock,
  Target
} from "lucide-react";

interface Step {
  number: number;
  icon: React.ReactNode;
  title: string;
  description: string;
  gradient: string;
  delay: string;
}

const steps: Step[] = [
  {
    number: 1,
    icon: <Lightbulb className="w-8 h-8" />,
    title: "Describe Your Goal",
    description: "Simply tell us what you want to achieve. Our AI understands natural language and captures all the details.",
    gradient: "from-primary to-primary-glow",
    delay: "0ms"
  },
  {
    number: 2,
    icon: <Brain className="w-8 h-8" />,
    title: "AI Analysis & Planning",
    description: "Our advanced AI breaks down your goal into actionable tasks, identifies dependencies, and estimates timelines.",
    gradient: "from-primary-glow to-accent",
    delay: "200ms"
  },
  {
    number: 3,
    icon: <BarChart3 className="w-8 h-8" />,
    title: "Visualize & Refine",
    description: "Review your personalized plan with beautiful visualizations, adjust priorities, and optimize your timeline.",
    gradient: "from-accent to-accent/80",
    delay: "400ms"
  },
  {
    number: 4,
    icon: <Rocket className="w-8 h-8" />,
    title: "Execute & Track",
    description: "Start working on your plan with real-time progress tracking, milestone alerts, and team collaboration tools.",
    gradient: "from-accent/80 to-success",
    delay: "600ms"
  }
];

export const HowItWorks = () => {
  return (
    <section className="py-20 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-mesh opacity-5 pointer-events-none"></div>
      
        <div className="container mx-auto px-4 relative z-10">
        {/* Section Header */}
        <div className="text-center mb-20 animate-fade-up">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-heading font-bold mb-6 bg-gradient-primary bg-clip-text text-transparent">
            How It Works
          </h2>
          <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
            From idea to execution in four simple steps
          </p>
        </div>

        {/* Horizontal Timeline Container */}
          <div className="relative max-w-7xl mx-auto">
          {/* Horizontal Timeline Line */}
          <div className="absolute top-16 left-20 right-20 h-1 bg-gradient-to-r from-primary via-primary-glow via-accent to-accent rounded-full shadow-lg opacity-80"></div>
          
          {/* Timeline Nodes on Line */}
          {/* {steps.map((step, index) => (
            <div key={`node-${index}`} className="absolute top-12 w-8 h-8 rounded-full bg-gradient-to-br from-primary to-primary-glow shadow-lg border-4 border-background flex items-center justify-center z-10" 
                 style={{ left: `calc(${20 + (index * 20)}% - 16px)` }}>
              <div className="w-3 h-3 rounded-full bg-white"></div>
            </div>
          ))} */}
          
          {/* Timeline Steps */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 pt-8">
            {steps.map((step, index) => (
              <div
                key={step.number}
                className="relative animate-fade-up"
                style={{ animationDelay: step.delay }}
              >
                {/* Glassmorphic Card */}
                <div className="group relative p-6 bg-card/80 backdrop-blur-sm hover:bg-card/90 transition-all duration-500 hover-magnetic hover:shadow-elevated rounded-2xl border border-border/50 overflow-hidden h-full">
                  {/* Gradient Border Effect */}
                  <div className={`absolute inset-0 bg-gradient-to-br ${step.gradient} opacity-0 group-hover:opacity-20 transition-opacity duration-500 blur-sm pointer-events-none`}></div>
                  
                  {/* Background Pattern */}
                  <div className="absolute inset-0 opacity-5 group-hover:opacity-10 transition-opacity duration-500 pointer-events-none">
                    {/* <div className="absolute top-4 right-4 w-8 h-8 bg-current rounded-full animate-pulse"></div>
                    <div className="absolute bottom-4 left-4 w-4 h-4 bg-current rounded-full animate-pulse" style={{animationDelay: '1s'}}></div>
                   */}
                   </div>

                  {/* Step Number Badge */}
                  {/* <div className={`inline-flex items-center justify-center w-10 h-10 rounded-full bg-gradient-to-br ${step.gradient} text-white font-bold text-lg mb-4 shadow-glow group-hover:scale-110 transition-transform duration-300`}>
                    {step.number}
                  </div> */}

                  {/* Icon */}
                  <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br ${step.gradient} text-white mb-4 shadow-glow group-hover:scale-110 transition-transform duration-300`}>
                    {step.icon}
                  </div>

                  {/* Content */}
                  <h3 className="text-lg font-semibold text-card-foreground mb-3 group-hover:text-primary transition-all duration-300">
                    {step.title}
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed group-hover:text-foreground/80 transition-colors duration-300">
                    {step.description}
                  </p>

                  {/* Hover Glow Effect */}
                  <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${step.gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-500 pointer-events-none`}></div>
                </div>

                {/* Timeline Node
                <div className="absolute -top-2 left-1/2 w-12 h-12 rounded-full glass-card border-4 border-background transform -translate-x-1/2 z-10 group hover-magnetic">
                  <div className={`w-full h-full rounded-full bg-gradient-to-br ${step.gradient} flex items-center justify-center text-white shadow-glow group-hover:scale-110 transition-transform duration-300`}>
                    {step.icon}
                  </div>
                </div> */}

                {/* Arrow Right (except for last step) */}
                {/* {index < steps.length - 1 && (
                  <div className="absolute -right-4 top-16 transform -translate-y-1/2 z-20 hidden lg:block">
                    <div className="w-6 h-6 rounded-full bg-primary shadow-lg flex items-center justify-center border-2 border-background">
                      <ArrowDown className="w-3 h-3 text-white rotate-90" />
                    </div>
                  </div>
                )} */}
              </div>
            ))}
          </div>
        </div>

      </div>
    </section>
  );
};
