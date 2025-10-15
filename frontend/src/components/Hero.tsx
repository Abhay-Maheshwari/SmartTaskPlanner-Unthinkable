import { ParticleBackground } from './ParticleBackground';

export const Hero = () => {
  return (
    <div className="relative text-center mb-16 animate-fade-up overflow-hidden">
      {/* Particle Background */}
      <ParticleBackground particleCount={60} />
      
      {/* Subtle Background Elements */}
      <div className="absolute inset-0 bg-gradient-mesh opacity-0 rounded-3xl -mx-4 -my-8 pointer-events-none"></div>
      
      {/* Floating 3D Elements */}
      <div className="absolute top-10 left-1/4 w-4 h-4 bg-primary/30 rounded-full animate-float hover-3d shadow-glow pointer-events-none"></div>
      <div className="absolute top-20 right-1/3 w-3 h-3 bg-accent/40 rounded-full animate-float hover-3d shadow-glow pointer-events-none" style={{animationDelay: '1s'}}></div>
      <div className="absolute bottom-10 left-1/3 w-5 h-5 bg-primary/25 rounded-full animate-float hover-3d shadow-glow pointer-events-none" style={{animationDelay: '2s'}}></div>
      <div className="absolute bottom-5 right-1/4 w-3 h-3 bg-accent/35 rounded-full animate-float hover-3d shadow-glow pointer-events-none" style={{animationDelay: '0.5s'}}></div>
      
      <div className="relative z-10">
        {/* Main Heading with Enhanced Effects */}
        <h1 className="text-6xl md:text-7xl lg:text-8xl font-heading font-bold mb-6 leading-tight">
          <span className="block bg-gradient-primary bg-clip-text text-transparent">
            Transform Your Goals
          </span>
          <span className="block bg-gradient-primary bg-clip-text text-transparent">
            into Actionable Plans
          </span>
        </h1>
        
        {/* Enhanced Subtitle */}
        <p className="text-xl md:text-2xl lg:text-3xl text-muted-foreground max-w-4xl mx-auto leading-relaxed mb-8 animate-slide-right">
          <span className="text-gradient-primary bg-clip-text text-transparent font-medium">
            AI-powered task planning
          </span>
          <span className="block mt-2">
            with smart dependencies and realistic timelines
          </span>
        </p>
        
        {/* Enhanced Feature badges with 3D effects */}
        <div className="flex flex-wrap justify-center gap-4 mb-12 animate-fade-up" style={{animationDelay: '0.3s'}}>
          <div className="group px-6 py-3 bg-primary/10 border border-primary/20 rounded-full text-sm font-medium text-primary hover:bg-primary/20 transition-all duration-300 hover-magnetic hover-3d shadow-soft hover:shadow-glow">
            <span className="inline-block animate-bounce" style={{animationDuration: '2s'}}>✨</span>
            <span className="ml-2">AI-Powered</span>
          </div>
          <div className="group px-6 py-3 bg-accent/10 border border-accent/20 rounded-full text-sm font-medium text-accent hover:bg-accent/20 transition-all duration-300 hover-magnetic hover-3d shadow-soft hover:shadow-glow">
            <span className="inline-block animate-bounce" style={{animationDuration: '2s', animationDelay: '0.5s'}}>🎯</span>
            <span className="ml-2">Smart Planning</span>
          </div>
          <div className="group px-6 py-3 bg-success/10 border border-success/20 rounded-full text-sm font-medium text-success hover:bg-success/20 transition-all duration-300 hover-magnetic hover-3d shadow-soft hover:shadow-glow">
            <span className="inline-block animate-bounce" style={{animationDuration: '2s', animationDelay: '1s'}}>⚡</span>
            <span className="ml-2">Real-time Updates</span>
          </div>
        </div>

        {/* CTA Button with Magnetic Effect */}


      </div>
    </div>
  );
};
