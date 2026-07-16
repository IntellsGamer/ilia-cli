import { StatusBar } from 'expo-status-bar'
import { Text, View, StyleSheet } from 'react-native'

export default function App() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{{ project_name }}</Text>
      <Text style={styles.desc}>{{ description }}</Text>
      <StatusBar style="auto" />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff' },
  title: { fontSize: 24, fontWeight: 'bold' },
  desc: { fontSize: 16, color: '#666', marginTop: 8 },
})
