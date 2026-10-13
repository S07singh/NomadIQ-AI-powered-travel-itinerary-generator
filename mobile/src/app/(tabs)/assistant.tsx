import { AudioModule, RecordingPresets, setAudioModeAsync, useAudioRecorder, useAudioRecorderState } from "expo-audio";
import * as Haptics from "expo-haptics";
import { router } from "expo-router";
import * as Speech from "expo-speech";
import { useRef, useState } from "react";
import { FlatList, KeyboardAvoidingView, Platform, Pressable, StyleSheet, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { ApiError, api } from "@/api/client";
import type { AssistantAction, AssistantMessage } from "@/api/types";
import { TalkIcon } from "@/components/icons";
import { OfferCard } from "@/components/offers";
import { Button, T } from "@/components/ui";
import { money } from "@/lib/format";
import { colors, fonts, radius } from "@/theme";

const STARTERS = ["Train from Delhi to Jaipur on Friday", "Plan 3 days in Udaipur", "Hotels in Goa next weekend"];

function local(content: string): AssistantMessage {
  return { id: `local-${Date.now()}-${Math.random()}`, role: "user", content, actions: [], created_at: new Date().toISOString() };
}

function Actions({ actions, onBook, busy }: { actions: AssistantAction[]; onBook: (offerId: string) => void; busy: boolean }) {
  return (
    <>
      {actions.map((a, i) => {
        if (a.type === "show_offers")
          return (
            <View key={i} style={{ marginTop: 6 }}>
              {a.data.results.map((o) => (
                <OfferCard key={o.offer_id} offer={o} action={<Button title="Book this" variant="quiet" disabled={busy} onPress={() => onBook(o.offer_id)} style={{ height: 42 }} />} />
              ))}
            </View>
          );
        if (a.type === "booking_quote")
          return (
            <View key={i} style={styles.quote}>
              <T>Price held at {money(a.data.price)}. Nothing is charged until you confirm.</T>
              <Button title="Review and pay" onPress={() => router.push(`/booking/${a.data.booking_id}`)} style={{ marginTop: 10 }} />
            </View>
          );
        if (a.type === "trip_created" || a.type === "trip_updated")
          return <Button key={i} title="Open the trip" variant="quiet" onPress={() => router.push(`/trip/${a.data.trip_id}`)} style={{ marginTop: 10, alignSelf: "flex-start" }} />;
        if (a.type === "needs_info" && a.data.missing.includes("saved_traveler"))
          return <Button key={i} title="Add traveler details" variant="quiet" onPress={() => router.push("/profile")} style={{ marginTop: 10, alignSelf: "flex-start" }} />;
        return null;
      })}
    </>
  );
}

export default function AssistantTab() {
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<FlatList<AssistantMessage>>(null);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const recState = useAudioRecorderState(recorder);

  const append = (...m: AssistantMessage[]) => setMessages((cur) => [...cur, ...m]);

  const send = async (message: string, selectedOfferId?: string) => {
    if (!message.trim() || busy) return;
    setBusy(true);
    setError(null);
    append(local(message));
    setText("");
    try {
      const reply = await api.ask({ message, conversation_id: conversationId, selected_offer_id: selectedOfferId });
      setConversationId(reply.conversation_id);
      append(reply.message);
    } catch (err) {
      setError((err as ApiError).message ?? "The assistant didn't answer. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const startTalking = async () => {
    if (busy) return;
    const perm = await AudioModule.requestRecordingPermissionsAsync();
    if (!perm.granted) {
      setError("Microphone access is off. Turn it on in Settings, or type instead.");
      return;
    }
    Speech.stop();
    await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true });
    await recorder.prepareToRecordAsync();
    recorder.record();
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => undefined);
  };

  const stopTalking = async () => {
    if (!recState.isRecording) return;
    await recorder.stop();
    await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false });
    const uri = recorder.uri;
    if (!uri) return;
    setBusy(true);
    setError(null);
    try {
      const reply = await api.voice(uri, { conversation_id: conversationId });
      setConversationId(reply.conversation_id);
      append(local(reply.transcript ?? "(voice)"), reply.message);
      Speech.speak(reply.message.content, { rate: 1.0 });
    } catch (err) {
      setError((err as ApiError).message ?? "Couldn't make out that recording. Try again or type.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.paper }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(m) => m.id}
          onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
          contentContainerStyle={{ padding: 16, gap: 16 }}
          ListHeaderComponent={
            <View>
              <T variant="display">Ask</T>
              <T style={{ color: colors.slate, marginTop: 6 }}>Hold the yellow button and speak, in English or Hindi. It can hold a fare for you; you always confirm before paying.</T>
              {messages.length === 0 ? (
                <View style={{ gap: 8, marginTop: 18 }}>
                  {STARTERS.map((s) => (
                    <Pressable key={s} accessibilityRole="button" onPress={() => send(s)} style={styles.starter}>
                      <T variant="label">{s}</T>
                    </Pressable>
                  ))}
                </View>
              ) : null}
            </View>
          }
          renderItem={({ item }) =>
            item.role === "user" ? (
              <View style={styles.user}>
                <T style={{ color: "#fff" }}>{item.content}</T>
              </View>
            ) : (
              <View style={styles.assistant}>
                <T>{item.content}</T>
                <Actions actions={item.actions} busy={busy} onBook={(id) => send("Book this one", id)} />
              </View>
            )
          }
          ListFooterComponent={
            <View>
              {busy ? <T variant="small">Working on it</T> : null}
              {error ? <T variant="small" style={{ color: colors.brick }}>{error}</T> : null}
            </View>
          }
        />

        <View style={styles.composer}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Hold to talk"
            accessibilityHint="Release to send your voice message"
            onPressIn={startTalking}
            onPressOut={stopTalking}
            disabled={busy}
            style={[styles.mic, recState.isRecording && { backgroundColor: colors.brick, transform: [{ scale: 1.08 }] }]}
          >
            <TalkIcon color={recState.isRecording ? "#fff" : colors.ink} />
          </Pressable>
          <TextInput
            value={text}
            onChangeText={setText}
            placeholder={recState.isRecording ? "Listening. Let go to send." : "Or type: sleeper bus to Goa Friday"}
            placeholderTextColor="#9AA3AE"
            onSubmitEditing={() => send(text)}
            returnKeyType="send"
            style={styles.input}
            accessibilityLabel="Message"
          />
          <Button title="Send" disabled={!text.trim() || busy} onPress={() => send(text)} style={{ height: 48, paddingHorizontal: 14 }} />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  starter: { borderWidth: 2, borderColor: colors.rule, backgroundColor: colors.sheet, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 12 },
  user: { alignSelf: "flex-end", maxWidth: "85%", backgroundColor: colors.ink, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 10 },
  assistant: { borderLeftWidth: 4, borderLeftColor: colors.ink, paddingLeft: 12 },
  quote: { marginTop: 10, borderLeftWidth: 4, borderLeftColor: colors.signal, backgroundColor: colors.sheet, padding: 12 },
  composer: { flexDirection: "row", alignItems: "center", gap: 8, padding: 10, borderTopWidth: 1, borderTopColor: colors.rule, backgroundColor: colors.sheet },
  mic: { width: 52, height: 52, borderRadius: 26, backgroundColor: colors.signal, alignItems: "center", justifyContent: "center" },
  input: { flex: 1, height: 48, fontFamily: fonts.regular, fontSize: 16, color: colors.ink, paddingHorizontal: 8 },
});
