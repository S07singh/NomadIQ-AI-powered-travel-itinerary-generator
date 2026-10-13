import { Tabs } from "expo-router";
import { PlanIcon, TalkIcon, TicketIcon, TripsIcon, YouIcon } from "@/components/icons";
import { colors, fonts } from "@/theme";

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.ink,
        tabBarInactiveTintColor: "#8A93A0",
        tabBarLabelStyle: { fontFamily: fonts.bold, fontSize: 11 },
        tabBarStyle: { backgroundColor: colors.sheet, borderTopColor: colors.rule, height: 64, paddingTop: 6 },
        sceneStyle: { backgroundColor: colors.paper },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Plan", tabBarIcon: ({ color }) => <PlanIcon color={color} /> }} />
      <Tabs.Screen name="trips" options={{ title: "Trips", tabBarIcon: ({ color }) => <TripsIcon color={color} /> }} />
      <Tabs.Screen name="assistant" options={{ title: "Ask", tabBarIcon: ({ color }) => <TalkIcon color={color} /> }} />
      <Tabs.Screen name="tickets" options={{ title: "Tickets", tabBarIcon: ({ color }) => <TicketIcon color={color} /> }} />
      <Tabs.Screen name="profile" options={{ title: "You", tabBarIcon: ({ color }) => <YouIcon color={color} /> }} />
    </Tabs>
  );
}
