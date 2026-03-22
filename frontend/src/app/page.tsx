import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Plane,
  MapPin,
  Sparkles,
  MessageSquare,
  Globe,
  Zap,
} from "lucide-react";

export default function Home() {
  return (
    <div className="bg-background">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50 dark:from-emerald-950/20 dark:via-teal-950/20 dark:to-cyan-950/20" />
        <div className="relative max-w-6xl mx-auto px-4 py-20 md:py-32">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 rounded-full px-4 py-1.5 text-sm font-medium mb-6">
              <Sparkles className="w-4 h-4" />
              AI-Powered Travel Planning
            </div>
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
              Plan Your Dream Trip{" "}
              <span className="bg-gradient-to-r from-emerald-500 to-teal-600 bg-clip-text text-transparent">
                in Seconds
              </span>
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground mb-10 leading-relaxed">
              Just tell us where you want to go. NomadIQ&apos;s AI agents research
              destinations, find hotels, discover restaurants, and craft your
              perfect day-by-day itinerary — all for free.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/plan">
                <Button
                  size="lg"
                  className="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white shadow-lg shadow-emerald-500/25 text-base px-8 py-6"
                >
                  <Plane className="w-5 h-5 mr-2" />
                  Start Planning — It&apos;s Free
                </Button>
              </Link>
              <Link href="/plans">
                <Button variant="outline" size="lg" className="text-base px-8 py-6">
                  View My Trips
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-6xl mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center mb-4">How It Works</h2>
        <p className="text-muted-foreground text-center mb-12 max-w-2xl mx-auto">
          Three simple steps to your perfect itinerary
        </p>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            {
              step: "1",
              title: "Tell Us Your Dream",
              desc: "Enter your destination, dates, budget, and travel style. Our smart form takes just 60 seconds.",
              icon: MapPin,
              color: "from-emerald-500 to-emerald-600",
            },
            {
              step: "2",
              title: "AI Agents Go to Work",
              desc: "5 specialized AI agents research destinations, hotels, restaurants, activities, and budget simultaneously.",
              icon: Zap,
              color: "from-teal-500 to-teal-600",
            },
            {
              step: "3",
              title: "Get Your Itinerary",
              desc: "Receive a complete day-by-day plan. Chat with AI to modify anything — add nightlife, change hotels, adjust budget.",
              icon: MessageSquare,
              color: "from-cyan-500 to-cyan-600",
            },
          ].map((item) => (
            <div key={item.step} className="text-center group">
              <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${item.color} flex items-center justify-center mx-auto mb-5 shadow-lg group-hover:scale-110 transition-transform`}>
                <item.icon className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-3">{item.title}</h3>
              <p className="text-muted-foreground leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="bg-muted/30 py-20">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            Why NomadIQ?
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { icon: Sparkles, title: "Multi-Agent AI", desc: "5 specialized AI agents collaborate to create comprehensive plans no single chatbot can match." },
              { icon: MessageSquare, title: "Chat to Modify", desc: "Don't like something? Just say \"make day 2 more adventurous\" and watch the plan update instantly." },
              { icon: Globe, title: "Any Destination", desc: "From Paris to Patagonia — get detailed local knowledge for any destination worldwide." },
              { icon: MapPin, title: "Day-by-Day Plans", desc: "Morning, afternoon, evening — every hour is planned with realistic timing and travel between spots." },
              { icon: Zap, title: "Instant & Free", desc: "No signup required. No credit card. Complete itineraries generated in under a minute." },
              { icon: Plane, title: "Everything Included", desc: "Hotels, restaurants, attractions, budget breakdown, local tips — all in one beautiful plan." },
            ].map((feat) => (
              <div key={feat.title} className="bg-background rounded-xl p-6 border hover:shadow-lg transition-shadow">
                <feat.icon className="w-8 h-8 text-emerald-500 mb-4" />
                <h3 className="font-semibold text-lg mb-2">{feat.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{feat.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-6xl mx-auto px-4 py-20 text-center">
        <h2 className="text-3xl font-bold mb-4">
          Ready to Plan Your Next Adventure?
        </h2>
        <p className="text-muted-foreground text-lg mb-8">
          Join thousands of travelers who plan smarter with AI.
        </p>
        <Link href="/plan">
          <Button
            size="lg"
            className="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white shadow-lg text-base px-10 py-6"
          >
            <Plane className="w-5 h-5 mr-2" /> Plan My Trip Now
          </Button>
        </Link>
      </section>
    </div>
  );
}
