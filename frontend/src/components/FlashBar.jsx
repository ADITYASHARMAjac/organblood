import React from 'react';

function FlashBar({ flash }) {
  if (!flash?.text) {
    return null;
  }

  return <div className={`flash ${flash.type || 'info'}`}>{flash.text}</div>;
}

export default FlashBar;
