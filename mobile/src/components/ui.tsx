import { Image } from "expo-image";
import type { ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type PressableProps,
  type StyleProp,
  type TextInputProps,
  type TextProps,
  type TextStyle,
  type ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { MediaImage } from "@/api/types";
import { colors, fonts, radius, space } from "@/theme";

type Variant = "display" | "title" | "heading" | "body" | "small" | "label";

const textStyles: Record<Variant, TextStyle> = {
  display: { fontFamily: fonts.heavy, fontSize: 40, lineHeight: 42, letterSpacing: -0.8, color: colors.ink },
  title: { fontFamily: fonts.heavy, fontSize: 28, lineHeight: 32, letterSpacing: -0.4, color: colors.ink },
  heading: { fontFamily: fonts.heavy, fontSize: 19, lineHeight: 24, color: colors.ink },
  body: { fontFamily: fonts.regular, fontSize: 16, lineHeight: 23, color: colors.ink },
  small: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 19, color: colors.slate },
  label: { fontFamily: fonts.bold, fontSize: 14, lineHeight: 18, color: colors.ink },
};

export function T({ variant = "body", style, ...props }: TextProps & { variant?: Variant }) {
  return <Text {...props} style={[textStyles[variant], { fontVariant: ["tabular-nums"] }, style]} />;
}

type ButtonVariant = "primary" | "ink" | "quiet" | "danger" | "signal";

export function Button({
  title,
  variant = "primary",
  busy,
  disabled,
  style,
  icon,
  ...props
}: PressableProps & { title: string; variant?: ButtonVariant; busy?: boolean; icon?: ReactNode; style?: StyleProp<ViewStyle> }) {
  const bg = { primary: colors.platform, ink: colors.ink, signal: colors.signal, quiet: "transparent", danger: "transparent" }[variant];
  const fg = { primary: "#fff", ink: "#fff", signal: colors.ink, quiet: colors.ink, danger: colors.brick }[variant];
  const border = variant === "quiet" ? colors.ink : variant === "danger" ? colors.brick : bg;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!(disabled || busy), busy: !!busy }}
      disabled={disabled || busy}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: bg, borderColor: border, opacity: disabled ? 0.45 : pressed ? 0.85 : 1 },
        style,
      ]}
      {...props}
    >
      {busy ? <ActivityIndicator color={fg} /> : icon}
      <Text style={[styles.buttonText, { color: fg }]}>{title}</Text>
    </Pressable>
  );
}

export function Field({ label, hint, error, style, ...props }: TextInputProps & { label: string; hint?: string; error?: string }) {
  return (
    <View style={[{ gap: 6 }, style as StyleProp<ViewStyle>]}>
      <T variant="label">{label}</T>
      <TextInput
        placeholderTextColor="#9AA3AE"
        accessibilityLabel={label}
        style={[styles.input, error ? { borderColor: colors.brick } : null]}
        {...props}
      />
      {error ? <T variant="small" style={{ color: colors.brick }}>{error}</T> : hint ? <T variant="small">{hint}</T> : null}
    </View>
  );
}

export function Notice({ children, tone = "error" }: { children: ReactNode; tone?: "error" | "success" | "info" }) {
  const color = tone === "error" ? colors.brick : tone === "success" ? colors.platformDeep : colors.ink;
  return (
    <View accessibilityRole="alert" style={[styles.notice, { borderLeftColor: color }]}>
      <T style={{ color }}>{children}</T>
    </View>
  );
}

export function Screen({ children, scroll = true, padded = true, edges = ["top"] }: { children: ReactNode; scroll?: boolean; padded?: boolean; edges?: ("top" | "bottom")[] }) {
  const inner = padded ? { paddingHorizontal: space.lg, paddingBottom: space.xxl } : null;
  return (
    <SafeAreaView edges={edges} style={{ flex: 1, backgroundColor: colors.paper }}>
      {scroll ? (
        <ScrollView contentContainerStyle={inner} keyboardShouldPersistTaps="handled">
          {children}
        </ScrollView>
      ) : (
        <View style={[{ flex: 1 }, inner]}>{children}</View>
      )}
    </SafeAreaView>
  );
}

export function Station({ filled = true, size = 18 }: { filled?: boolean; size?: number }) {
  return (
    <View
      accessible={false}
      style={{ width: size, height: size, borderRadius: size / 2, borderWidth: size > 14 ? 4 : 3, borderColor: colors.ink, backgroundColor: filled ? colors.signal : colors.sheet }}
    />
  );
}

export function Chip({ label, on, onPress }: { label: string; on?: boolean; onPress?: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: !!on }}
      onPress={onPress}
      style={[styles.chip, on ? { backgroundColor: colors.ink, borderColor: colors.ink } : null]}
    >
      <Text style={[styles.chipText, on ? { color: "#fff" } : null]}>{label}</Text>
    </Pressable>
  );
}

export function Photo({ image, style, thumb }: { image?: MediaImage | null; style?: StyleProp<ViewStyle>; thumb?: boolean }) {
  const uri = image ? (thumb && image.thumbnail_url) || image.url : null;
  return (
    <View style={[{ backgroundColor: "#E3E7EC", overflow: "hidden", borderRadius: radius.sm }, style]}>
      {uri ? <Image source={{ uri }} style={StyleSheet.absoluteFill} contentFit="cover" transition={180} accessibilityLabel={image?.alt} /> : null}
    </View>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 48 }} accessibilityRole="progressbar">
      <ActivityIndicator color={colors.ink} />
      <T variant="small">{label}</T>
    </View>
  );
}

export function Rule() {
  return <View style={{ height: StyleSheet.hairlineWidth * 2, backgroundColor: colors.rule }} />;
}

const styles = StyleSheet.create({
  button: { height: 50, borderRadius: radius.md, borderWidth: 2, paddingHorizontal: 18, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
  buttonText: { fontFamily: fonts.bold, fontSize: 16 },
  input: { height: 50, borderWidth: 2, borderColor: colors.rule, borderRadius: radius.md, backgroundColor: colors.sheet, paddingHorizontal: 12, fontFamily: fonts.regular, fontSize: 16, color: colors.ink },
  notice: { borderLeftWidth: 4, backgroundColor: colors.sheet, paddingHorizontal: 14, paddingVertical: 10, borderTopRightRadius: radius.md, borderBottomRightRadius: radius.md },
  chip: { height: 40, paddingHorizontal: 16, borderRadius: 20, borderWidth: 2, borderColor: colors.rule, backgroundColor: colors.sheet, justifyContent: "center" },
  chipText: { fontFamily: fonts.semibold, fontSize: 15, color: colors.ink, textTransform: "capitalize" },
});
