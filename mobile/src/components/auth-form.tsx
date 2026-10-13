import { router } from "expo-router";
import { useState } from "react";
import { View } from "react-native";
import { ApiError } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { colors } from "@/theme";
import { Button, Field, Notice, Screen, T } from "./ui";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const { login, register } = useAuth();
  const isSignup = mode === "signup";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      if (isSignup) await register(name.trim(), email.trim(), password);
      else await login(email.trim(), password);
      // The protected stack swaps to the tabs automatically once `user` is set.
    } catch (err) {
      const e = err as ApiError;
      setError(
        e.code === "invalid_credentials"
          ? "That email and password don't match."
          : e.code === "email_taken"
            ? "There's already an account with this email. Sign in instead."
            : e.code === "validation_error"
              ? "Passwords need 8+ characters with letters and numbers."
              : e.message ?? "Something went wrong. Try again.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen edges={["bottom"]}>
      <T variant="display" style={{ marginTop: 8 }}>{isSignup ? "Create your account" : "Welcome back"}</T>
      <T style={{ color: colors.slate, marginTop: 8 }}>
        {isSignup ? "Save trips, keep traveler details, and book in one step." : "Your trips and bookings are where you left them."}
      </T>
      <View style={{ gap: 18, marginTop: 28 }}>
        {isSignup ? <Field label="Name" autoComplete="name" textContentType="name" value={name} onChangeText={setName} /> : null}
        <Field label="Email" autoComplete="email" textContentType="emailAddress" keyboardType="email-address" autoCapitalize="none" value={email} onChangeText={setEmail} />
        <Field
          label="Password"
          secureTextEntry
          autoComplete={isSignup ? "new-password" : "current-password"}
          textContentType={isSignup ? "newPassword" : "password"}
          hint={isSignup ? "At least 8 characters, with letters and numbers." : undefined}
          value={password}
          onChangeText={setPassword}
          onSubmitEditing={submit}
        />
        {error ? <Notice>{error}</Notice> : null}
        <Button title={isSignup ? "Create account" : "Sign in"} busy={busy} disabled={!email || !password || (isSignup && !name)} onPress={submit} />
        <Button title={isSignup ? "I already have an account" : "Create an account instead"} variant="quiet" onPress={() => router.replace(isSignup ? "/login" : "/signup")} />
      </View>
    </Screen>
  );
}
