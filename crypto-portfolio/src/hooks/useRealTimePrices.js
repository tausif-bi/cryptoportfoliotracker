import { useState, useEffect, useCallback } from 'react';
import priceService from '../services/priceService';

export const useRealTimePrices = (symbols) => {
  const [prices, setPrices] = useState({});
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!symbols || symbols.length === 0) {
      return;
    }

    // Price update handler
    const handlePriceUpdate = (newPrices) => {
      setPrices(newPrices);
      setConnected(true);
    };

    // Start price updates
    const stopUpdates = priceService.startPriceUpdates(
      symbols,
      handlePriceUpdate,
      30000 // Update every 30 seconds
    );

    // Cleanup
    return () => {
      stopUpdates();
      setConnected(false);
    };
  }, [symbols.join(',')]);

  return { prices, connected };
};