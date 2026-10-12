import {
  Overpass_400Regular,
  Overpass_600SemiBold,
  Overpass_700Bold,
  Overpass_800ExtraBold,
  useFonts,
} from "@expo-google-fonts/overpass";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AuthProvider, useAuth } from "@/auth/AuthContext";
import { colors, fonts } from "@/theme";

SplashScreen.preventAutoHideAsync().catch(() => undefined);

const header = {
  headerShown: true,
  headerTitle: "",
  headerShadowVisible: false,
  headerStyle: { backgroundColor: colors.paper },
  headerTintColor: colors.ink,
  headerTitleStyle: { fontFamily: fonts.bold },
  headerBackButtonDisplayMode: "minimal" as const,
};

function RootNavigator() {
  const { user, ready } = useAuth();
  const [fontsLoaded] = useFonts({ Overpass_400Regular, Overpass_600SemiBold, Overpass_700Bold, Overpass_800ExtraBold });

  useEffect(() => {
    if (ready && fontsLoaded) SplashScreen.hideAsync().catch(() => undefined);
  }, [ready, fontsLoaded]);

  if (!ready || !fontsLoaded) return null;

  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.paper } }}>
      <Stack.Protected guard={!!user}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="trip/[id]" options={header} />
        <Stack.Screen name="trip/new" options={{ ...header, headerTitle: "New trip", presentation: "modal" }} />
        <Stack.Screen name="booking/[id]" options={header} />
        <Stack.Screen name="bookings" options={{ ...header, headerTitle: "Bookings" }} />
        <Stack.Screen name="explore/[place]" options={header} />
      </Stack.Protected>
      <Stack.Protected guard={!user}>
        <Stack.Screen name="welcome" />
        <Stack.Screen name="login" options={header} />
        <Stack.Screen name="signup" options={header} />
      </Stack.Protected>
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <StatusBar style="dark" />
        <RootNavigator />
      </AuthProvider>
    </SafeAreaProvider>
  );
}
