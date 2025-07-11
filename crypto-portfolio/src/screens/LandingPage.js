import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  Platform,
  Linking,
  Image,
} from 'react-native';
import * as Animatable from 'react-native-animatable';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeContext';
import { useNavigation } from '@react-navigation/native';

const { width, height } = Dimensions.get('window');

const LandingPage = () => {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const [isVideoLoaded, setIsVideoLoaded] = useState(false);
  const scrollViewRef = useRef(null);

  // Custom animations
  const fadeInUp = {
    from: { opacity: 0, translateY: 30 },
    to: { opacity: 1, translateY: 0 },
  };

  const fadeInLeft = {
    from: { opacity: 0, translateX: -30 },
    to: { opacity: 1, translateX: 0 },
  };

  const fadeInRight = {
    from: { opacity: 0, translateX: 30 },
    to: { opacity: 1, translateX: 0 },
  };

  const features = [
    {
      icon: 'trending-up',
      title: 'Real-Time Portfolio Tracking',
      description: 'Monitor your crypto investments across multiple exchanges in real-time',
      color: '#00FF88',
    },
    {
      icon: 'analytics',
      title: 'AI-Powered Strategies',
      description: 'Advanced trading strategies powered by machine learning algorithms',
      color: '#00B4FF',
    },
    {
      icon: 'bar-chart',
      title: 'Interactive Charts',
      description: 'Professional TradingView charts with zoom, pan, and technical indicators',
      color: '#FF6B6B',
    },
    {
      icon: 'shield-checkmark',
      title: 'Secure & Private',
      description: 'Bank-level security with encrypted credentials and JWT authentication',
      color: '#FFD93D',
    },
    {
      icon: 'swap-horizontal',
      title: 'Multi-Exchange Support',
      description: 'Connect to Binance, Coinbase, and 100+ other exchanges',
      color: '#A78BFA',
    },
    {
      icon: 'notifications',
      title: 'Smart Alerts',
      description: 'Get notified about trading signals and portfolio changes',
      color: '#34D399',
    },
  ];

  const howItWorks = [
    {
      step: 1,
      title: 'Connect Your Exchange',
      description: 'Securely link your exchange accounts with API keys',
      icon: 'link',
    },
    {
      step: 2,
      title: 'Choose Trading Strategies',
      description: 'Select from our AI-powered strategies or create custom ones',
      icon: 'options',
    },
    {
      step: 3,
      title: 'Monitor Performance',
      description: 'Track your portfolio and strategy performance in real-time',
      icon: 'stats-chart',
    },
    {
      step: 4,
      title: 'Optimize & Profit',
      description: 'Use insights to optimize your trading and maximize returns',
      icon: 'rocket',
    },
  ];

  const scrollToSection = (sectionId) => {
    // For web, use smooth scrolling
    if (Platform.OS === 'web') {
      const element = document.getElementById(sectionId);
      element?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      // For mobile platforms, use ScrollView ref
      if (sectionId === 'demo' && scrollViewRef.current) {
        scrollViewRef.current.scrollTo({ y: height * 2.5, animated: true });
      }
    }
  };

  const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.colors.background,
    },
    heroSection: {
      height: Platform.OS === 'web' ? height * 0.9 : height - 100,
      position: 'relative',
      overflow: 'hidden',
    },
    videoBackground: {
      position: 'absolute',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      opacity: 0.3,
    },
    heroContent: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 20,
      zIndex: 2,
    },
    heroTitle: {
      fontSize: Platform.OS === 'web' ? 48 : 36,
      fontWeight: 'bold',
      color: theme.colors.text,
      textAlign: 'center',
      marginBottom: 20,
    },
    heroSubtitle: {
      fontSize: Platform.OS === 'web' ? 20 : 18,
      color: '#FFFFFF',
      textAlign: 'center',
      marginBottom: 40,
      paddingHorizontal: 20,
    },
    ctaContainer: {
      flexDirection: 'row',
      gap: 20,
    },
    ctaButton: {
      paddingHorizontal: 30,
      paddingVertical: 15,
      borderRadius: 25,
      overflow: 'hidden',
    },
    ctaButtonText: {
      color: '#FFFFFF',
      fontSize: 16,
      fontWeight: 'bold',
    },
    secondaryButton: {
      borderWidth: 2,
      borderColor: theme.colors.primary,
      backgroundColor: 'transparent',
      paddingHorizontal: 30,
      paddingVertical: 15,
      borderRadius: 25,
    },
    secondaryButtonText: {
      color: theme.colors.primary,
      fontSize: 16,
      fontWeight: 'bold',
    },
    section: {
      padding: Platform.OS === 'web' ? 60 : 40,
      alignItems: 'center',
    },
    sectionTitle: {
      fontSize: Platform.OS === 'web' ? 36 : 28,
      fontWeight: 'bold',
      color: theme.colors.text,
      marginBottom: 20,
      textAlign: 'center',
    },
    sectionSubtitle: {
      fontSize: 18,
      color: theme.colors.subText,
      marginBottom: 40,
      textAlign: 'center',
      maxWidth: 600,
    },
    featuresGrid: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      justifyContent: 'center',
      gap: 20,
      maxWidth: 1200,
    },
    featureCard: {
      backgroundColor: theme.colors.cardBackground,
      borderRadius: 20,
      padding: 30,
      width: Platform.OS === 'web' ? 350 : width - 80,
      alignItems: 'center',
      borderWidth: 1,
      borderColor: theme.colors.border,
    },
    featureIcon: {
      width: 60,
      height: 60,
      borderRadius: 30,
      justifyContent: 'center',
      alignItems: 'center',
      marginBottom: 20,
    },
    featureTitle: {
      fontSize: 20,
      fontWeight: 'bold',
      color: theme.colors.text,
      marginBottom: 10,
      textAlign: 'center',
    },
    featureDescription: {
      fontSize: 16,
      color: '#FFFFFF',
      textAlign: 'center',
      lineHeight: 24,
    },
    howItWorksContainer: {
      maxWidth: 800,
      width: '100%',
    },
    stepCard: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 30,
      backgroundColor: theme.colors.cardBackground,
      borderRadius: 15,
      padding: 20,
      borderWidth: 1,
      borderColor: theme.colors.border,
    },
    stepNumber: {
      width: 50,
      height: 50,
      borderRadius: 25,
      backgroundColor: theme.colors.primary,
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: 20,
    },
    stepNumberText: {
      color: '#FFFFFF',
      fontSize: 20,
      fontWeight: 'bold',
    },
    stepContent: {
      flex: 1,
    },
    stepTitle: {
      fontSize: 18,
      fontWeight: 'bold',
      color: theme.colors.text,
      marginBottom: 5,
    },
    stepDescription: {
      fontSize: 16,
      color: '#FFFFFF',
      lineHeight: 22,
    },
    demoSection: {
      backgroundColor: theme.colors.cardBackground,
      borderRadius: 20,
      padding: 40,
      maxWidth: 1000,
      width: '100%',
      alignItems: 'center',
    },
    demoTitle: {
      fontSize: 24,
      fontWeight: 'bold',
      color: theme.colors.text,
      marginBottom: 20,
    },
    videoPlaceholder: {
      width: '100%',
      height: Platform.OS === 'web' ? 500 : 300,
      backgroundColor: theme.colors.background,
      borderRadius: 15,
      justifyContent: 'center',
      alignItems: 'center',
      borderWidth: 1,
      borderColor: theme.colors.border,
    },
    playButton: {
      width: 80,
      height: 80,
      borderRadius: 40,
      backgroundColor: theme.colors.primary,
      justifyContent: 'center',
      alignItems: 'center',
    },
    footer: {
      backgroundColor: theme.colors.cardBackground,
      padding: 40,
      alignItems: 'center',
    },
    footerText: {
      color: theme.colors.subText,
      fontSize: 14,
      marginBottom: 20,
    },
    socialLinks: {
      flexDirection: 'row',
      gap: 20,
    },
    particleContainer: {
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      zIndex: 1,
    },
    particle: {
      position: 'absolute',
      width: 4,
      height: 4,
      borderRadius: 2,
      backgroundColor: theme.colors.primary,
      opacity: 0.5,
    },
  });

  // Particle animation component
  const ParticleAnimation = () => {
    const particles = Array(20).fill(null).map((_, i) => ({
      id: i,
      x: Math.random() * width,
      y: Math.random() * height,
      duration: 20000 + Math.random() * 10000,
    }));

    return (
      <View style={styles.particleContainer} pointerEvents="none">
        {particles.map((particle) => (
          <Animatable.View
            key={particle.id}
            style={[
              styles.particle,
              {
                left: particle.x,
                top: particle.y,
              },
            ]}
            animation={{
              0: { translateY: 0, opacity: 0 },
              0.1: { opacity: 0.5 },
              0.9: { opacity: 0.5 },
              1: { translateY: -height, opacity: 0 },
            }}
            duration={particle.duration}
            iterationCount="infinite"
            easing="linear"
          />
        ))}
      </View>
    );
  };

  if (Platform.OS === 'web') {
    return (
      <ScrollView 
        ref={scrollViewRef}
        showsVerticalScrollIndicator={true}
        scrollEnabled={true}
        style={{ 
          flex: 1, 
          backgroundColor: theme.colors.background,
          height: '100vh',
          overflow: 'auto',
        }}
      >
        <View style={{ minHeight: '100%' }}>
      {/* Hero Section */}
      <View style={styles.heroSection} id="hero">
        <LinearGradient
          colors={[theme.colors.primary + '20', theme.colors.background]}
          style={StyleSheet.absoluteFillObject}
        />
        
        {Platform.OS === 'web' && <ParticleAnimation />}
        
        <View style={styles.heroContent}>
          <Animatable.Text
            animation={fadeInUp}
            duration={1000}
            style={styles.heroTitle}
          >
            Advanced Crypto Portfolio Tracker
          </Animatable.Text>
          
          <Animatable.Text
            animation={fadeInUp}
            duration={1000}
            delay={200}
            style={styles.heroSubtitle}
          >
            Track, analyze, and optimize your cryptocurrency investments with AI-powered trading strategies
          </Animatable.Text>
          
          <Animatable.View
            animation={fadeInUp}
            duration={1000}
            delay={400}
            style={styles.ctaContainer}
          >
            <TouchableOpacity
              onPress={() => navigation.navigate('Auth', { screen: 'Register' })}
            >
              <LinearGradient
                colors={[theme.colors.primary, theme.colors.primary + 'CC']}
                style={styles.ctaButton}
              >
                <Text style={styles.ctaButtonText}>Get Started Free</Text>
              </LinearGradient>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.secondaryButton}
              onPress={() => scrollToSection('demo')}
            >
              <Text style={styles.secondaryButtonText}>Watch Demo</Text>
            </TouchableOpacity>
          </Animatable.View>
          
          <Animatable.View
            animation={fadeInUp}
            duration={1000}
            delay={600}
            style={{ marginTop: 30 }}
          >
            <TouchableOpacity
              onPress={() => navigation.navigate('Auth', { screen: 'Login' })}
            >
              <Text style={{ color: theme.colors.subText, fontSize: 16 }}>
                Already have an account? <Text style={{ color: theme.colors.primary, fontWeight: 'bold' }}>Sign In</Text>
              </Text>
            </TouchableOpacity>
          </Animatable.View>
        </View>
      </View>

      {/* Features Section */}
      <View style={styles.section} id="features">
        <Animatable.Text
          animation={fadeInUp}
          duration={800}
          style={styles.sectionTitle}
        >
          Powerful Features
        </Animatable.Text>
        
        <Animatable.Text
          animation={fadeInUp}
          duration={800}
          delay={200}
          style={styles.sectionSubtitle}
        >
          Everything you need to succeed in crypto trading
        </Animatable.Text>
        
        <View style={styles.featuresGrid}>
          {features.map((feature, index) => (
            <Animatable.View
              key={index}
              animation={fadeInUp}
              duration={800}
              delay={400 + index * 100}
              style={styles.featureCard}
            >
              <View style={[styles.featureIcon, { backgroundColor: feature.color + '20' }]}>
                <Ionicons name={feature.icon} size={30} color={feature.color} />
              </View>
              <Text style={styles.featureTitle}>{feature.title}</Text>
              <Text style={styles.featureDescription}>{feature.description}</Text>
            </Animatable.View>
          ))}
        </View>
      </View>

      {/* How It Works Section */}
      <View style={[styles.section, { backgroundColor: theme.colors.cardBackground }]} id="how-it-works">
        <Animatable.Text
          animation={fadeInUp}
          duration={800}
          style={styles.sectionTitle}
        >
          How It Works
        </Animatable.Text>
        
        <Animatable.Text
          animation={fadeInUp}
          duration={800}
          delay={200}
          style={styles.sectionSubtitle}
        >
          Get started in just 4 simple steps
        </Animatable.Text>
        
        <View style={styles.howItWorksContainer}>
          {howItWorks.map((step, index) => (
            <Animatable.View
              key={index}
              animation={index % 2 === 0 ? fadeInLeft : fadeInRight}
              duration={800}
              delay={400 + index * 100}
              style={styles.stepCard}
            >
              <View style={styles.stepNumber}>
                <Text style={styles.stepNumberText}>{step.step}</Text>
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>{step.title}</Text>
                <Text style={styles.stepDescription}>{step.description}</Text>
              </View>
            </Animatable.View>
          ))}
        </View>
      </View>

      {/* Demo Section */}
      <View style={styles.section} id="demo">
        <Animatable.View
          animation={fadeInUp}
          duration={800}
          style={styles.demoSection}
        >
          <Text style={styles.demoTitle}>See It In Action</Text>
          
          <TouchableOpacity
            style={styles.videoPlaceholder}
            onPress={() => {
              // Open demo video
              if (Platform.OS === 'web') {
                window.open('https://www.youtube.com/watch?v=dQw4w9WgXcQ', '_blank');
              } else {
                Linking.openURL('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
              }
            }}
          >
            <View style={styles.playButton}>
              <Ionicons name="play" size={40} color="#FFFFFF" />
            </View>
          </TouchableOpacity>
        </Animatable.View>
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>© 2024 Crypto Portfolio Tracker. All rights reserved.</Text>
        <View style={styles.socialLinks}>
          <TouchableOpacity onPress={() => Linking.openURL('https://twitter.com')}>
            <Ionicons name="logo-twitter" size={24} color={theme.colors.subText} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => Linking.openURL('https://github.com')}>
            <Ionicons name="logo-github" size={24} color={theme.colors.subText} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => Linking.openURL('https://linkedin.com')}>
            <Ionicons name="logo-linkedin" size={24} color={theme.colors.subText} />
          </TouchableOpacity>
        </View>
      </View>
        </View>
      </ScrollView>
    );
  }

  // Mobile version
  return (
    <View style={{ flex: 1 }}>
      <ScrollView 
        ref={scrollViewRef}
        showsVerticalScrollIndicator={true}
        bounces={true}
        scrollEnabled={true}
        contentContainerStyle={{ 
          flexGrow: 1,
        }}
        style={{ flex: 1, backgroundColor: theme.colors.background }}
      >
      {/* Hero Section */}
      <View style={styles.heroSection} id="hero">
        <LinearGradient
          colors={[theme.colors.primary + '20', theme.colors.background]}
          style={StyleSheet.absoluteFillObject}
        />
        
        {Platform.OS === 'web' && <ParticleAnimation />}
        
        <View style={styles.heroContent}>
          <Animatable.Text
            animation={fadeInUp}
            duration={1000}
            style={styles.heroTitle}
          >
            Advanced Crypto Portfolio Tracker
          </Animatable.Text>
          
          <Animatable.Text
            animation={fadeInUp}
            duration={1000}
            delay={200}
            style={styles.heroSubtitle}
          >
            Track, analyze, and optimize your cryptocurrency investments with AI-powered trading strategies
          </Animatable.Text>
          
          <Animatable.View
            animation={fadeInUp}
            duration={1000}
            delay={400}
            style={styles.ctaContainer}
          >
            <TouchableOpacity
              onPress={() => navigation.navigate('Auth', { screen: 'Register' })}
            >
              <LinearGradient
                colors={[theme.colors.primary, theme.colors.primary + 'CC']}
                style={styles.ctaButton}
              >
                <Text style={styles.ctaButtonText}>Get Started Free</Text>
              </LinearGradient>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.secondaryButton}
              onPress={() => scrollToSection('demo')}
            >
              <Text style={styles.secondaryButtonText}>Watch Demo</Text>
            </TouchableOpacity>
          </Animatable.View>
          
          <Animatable.View
            animation={fadeInUp}
            duration={1000}
            delay={600}
            style={{ marginTop: 30 }}
          >
            <TouchableOpacity
              onPress={() => navigation.navigate('Auth', { screen: 'Login' })}
            >
              <Text style={{ color: theme.colors.subText, fontSize: 16 }}>
                Already have an account? <Text style={{ color: theme.colors.primary, fontWeight: 'bold' }}>Sign In</Text>
              </Text>
            </TouchableOpacity>
          </Animatable.View>
        </View>
      </View>

      {/* Features Section */}
      <View style={styles.section} id="features">
        <Animatable.Text
          animation={fadeInUp}
          duration={800}
          style={styles.sectionTitle}
        >
          Powerful Features
        </Animatable.Text>
        
        <Animatable.Text
          animation={fadeInUp}
          duration={800}
          delay={200}
          style={styles.sectionSubtitle}
        >
          Everything you need to succeed in crypto trading
        </Animatable.Text>
        
        <View style={styles.featuresGrid}>
          {features.map((feature, index) => (
            <Animatable.View
              key={index}
              animation={fadeInUp}
              duration={800}
              delay={400 + index * 100}
              style={styles.featureCard}
            >
              <View style={[styles.featureIcon, { backgroundColor: feature.color + '20' }]}>
                <Ionicons name={feature.icon} size={30} color={feature.color} />
              </View>
              <Text style={styles.featureTitle}>{feature.title}</Text>
              <Text style={styles.featureDescription}>{feature.description}</Text>
            </Animatable.View>
          ))}
        </View>
      </View>

      {/* How It Works Section */}
      <View style={[styles.section, { backgroundColor: theme.colors.cardBackground }]} id="how-it-works">
        <Animatable.Text
          animation={fadeInUp}
          duration={800}
          style={styles.sectionTitle}
        >
          How It Works
        </Animatable.Text>
        
        <Animatable.Text
          animation={fadeInUp}
          duration={800}
          delay={200}
          style={styles.sectionSubtitle}
        >
          Get started in just 4 simple steps
        </Animatable.Text>
        
        <View style={styles.howItWorksContainer}>
          {howItWorks.map((step, index) => (
            <Animatable.View
              key={index}
              animation={index % 2 === 0 ? fadeInLeft : fadeInRight}
              duration={800}
              delay={400 + index * 100}
              style={styles.stepCard}
            >
              <View style={styles.stepNumber}>
                <Text style={styles.stepNumberText}>{step.step}</Text>
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>{step.title}</Text>
                <Text style={styles.stepDescription}>{step.description}</Text>
              </View>
            </Animatable.View>
          ))}
        </View>
      </View>

      {/* Demo Section */}
      <View style={styles.section} id="demo">
        <Animatable.View
          animation={fadeInUp}
          duration={800}
          style={styles.demoSection}
        >
          <Text style={styles.demoTitle}>See It In Action</Text>
          
          <TouchableOpacity
            style={styles.videoPlaceholder}
            onPress={() => {
              // Open demo video
              if (Platform.OS === 'web') {
                window.open('https://www.youtube.com/watch?v=dQw4w9WgXcQ', '_blank');
              } else {
                Linking.openURL('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
              }
            }}
          >
            <View style={styles.playButton}>
              <Ionicons name="play" size={40} color="#FFFFFF" />
            </View>
          </TouchableOpacity>
        </Animatable.View>
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>© 2024 Crypto Portfolio Tracker. All rights reserved.</Text>
        <View style={styles.socialLinks}>
          <TouchableOpacity onPress={() => Linking.openURL('https://twitter.com')}>
            <Ionicons name="logo-twitter" size={24} color={theme.colors.subText} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => Linking.openURL('https://github.com')}>
            <Ionicons name="logo-github" size={24} color={theme.colors.subText} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => Linking.openURL('https://linkedin.com')}>
            <Ionicons name="logo-linkedin" size={24} color={theme.colors.subText} />
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
    </View>
  );
};

export default LandingPage;